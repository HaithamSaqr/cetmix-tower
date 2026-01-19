# Copyright (C) 2024 Cetmix OÜ
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class CxTowerJetWaypoint(models.Model):
    """Jet Waypoints represent waypoints for jets"""

    _name = "cx.tower.jet.waypoint"
    _description = "Cetmix Tower Jet Waypoint"
    _inherit = ["cx.tower.reference.mixin", "cx.tower.access.mixin"]
    _order = "create_date desc"

    name = fields.Char(required=True)
    access_level = fields.Selection(
        compute="_compute_access_level", readonly=False, store=True
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("preparing", "Preparing"),
            ("ready", "Ready"),
            ("error", "Error"),
            ("arriving", "Arriving"),
            ("leaving", "Leaving"),
            ("deleting", "Deleting"),
        ],
        default="draft",
        required=True,
        readonly=False,
    )
    can_fly = fields.Boolean(
        compute="_compute_can_fly",
        readonly=True,
    )
    is_current = fields.Boolean(
        compute="_compute_is_current",
        readonly=True,
    )
    jet_id = fields.Many2one(
        comodel_name="cx.tower.jet",
        required=True,
        ondelete="cascade",
        help="Jet this waypoint belongs to",
    )
    jet_template_id = fields.Many2one(
        comodel_name="cx.tower.jet.template",
        related="jet_id.jet_template_id",
        readonly=True,
    )
    waypoint_template_id = fields.Many2one(
        string="Type",
        comodel_name="cx.tower.jet.waypoint.template",
        help="Waypoint template this waypoint is based on",
        domain="[('jet_template_id', '=', jet_template_id)]",
        required=True,
    )
    variable_values = fields.Json(
        help="Custom variable values for this waypoint",
        readonly=True,
    )
    metadata = fields.Json(
        help="Additional metadata for this waypoint",
        readonly=True,
    )

    # ------------------------------------
    # --------- Computed Fields ---------
    # ------------------------------------
    @api.depends("waypoint_template_id")
    def _compute_access_level(self):
        """
        Compute the access level of the waypoint
        NB: it doesn't change if the waypoint template access level changes
        """
        for waypoint in self:
            waypoint.access_level = waypoint.waypoint_template_id.access_level

    @api.depends("jet_id.waypoint_id")
    def _compute_is_current(self):
        """
        Is current waypoint if it is the current waypoint of the jet
        """
        for waypoint in self:
            waypoint.is_current = waypoint.id == waypoint.jet_id.waypoint_id.id

    @api.depends("jet_id.waypoint_ids", "jet_id.waypoint_ids.state")
    def _compute_can_fly(self):
        """
        Can fly only if waypoint is in the ready state and
        is not the current waypoint and all the jet waypoints
        are in the "ready" state
        """
        for waypoint in self:
            all_waypoints = waypoint.jet_id.waypoint_ids
            waypoint.can_fly = (
                waypoint.state == "ready"
                and waypoint.id != waypoint.jet_id.waypoint_id.id
                and not bool(
                    all_waypoints.filtered(lambda w: w.state not in ["ready", "error"])
                )
            )

    # ------------------------------------
    # --------- Waypoint Setters ---------
    # ------------------------------------
    def prepare(self):
        """
        Handle the waypoint creation event

        Returns:
            bool: True if event was handled else False
        """
        self.ensure_one()
        if not self.state == "draft":
            return False
        if self.waypoint_template_id.plan_create_id:
            self.state = "preparing"
            self.jet_id.run_flight_plan(
                flight_plan=self.waypoint_template_id.plan_create_id,
                plan_log={
                    "waypoint_id": self.id,
                },
            )
        else:
            self.state = "ready"
        return True

    def fly_to(self):
        """
        Fly to the waypoint
        """
        self.ensure_one()
        if not self.state == "ready":
            return False

        # Cannot fly to waypoint if there is another waypoint
        #  in the "arriving" or state
        if self.jet_id.waypoint_ids.filtered(
            lambda w: w.state in ["arriving", "leaving"]
        ):
            return False

        # Leave the previous waypoint
        current_waypoint = self.jet_id.waypoint_id
        if not current_waypoint:
            self.state = "arriving"
            self.arrive()
            return True

        # Don't go to the waypoint if it is already the current waypoint
        if current_waypoint.id == self.id:
            return True

        # Cannot leave the waypoint if it is not ready
        if not current_waypoint.state == "ready":
            return False

        # Set the new waypoint state to arriving
        self.state = "arriving"
        # Leave the previous waypoint
        current_waypoint.leave()
        # If leaving completed immediately (no plan_leave_id),
        # arrive at the new waypoint
        if current_waypoint.state == "ready":
            self.arrive()
        return True

    def leave(self):
        """
        Leave the waypoint

        Returns:
            bool: True if event was handled else False
        """
        self.ensure_one()
        if not self.state == "ready":
            return False
        self.state = "leaving"
        plan_leave = self.waypoint_template_id.plan_leave_id
        if plan_leave:
            self.jet_id.run_flight_plan(
                flight_plan=plan_leave,
                plan_log={
                    "waypoint_id": self.id,
                },
            )
        else:
            self.state = "ready"
        return True

    def arrive(self):
        """
        Arrive at the waypoint

        Returns:
            bool: True if event was handled else False
        """
        self.ensure_one()
        if not self.state == "arriving":
            return False
        plan_arrive = self.waypoint_template_id.plan_arrive_id
        if plan_arrive:
            self.jet_id.run_flight_plan(
                flight_plan=plan_arrive,
                plan_log={
                    "waypoint_id": self.id,
                },
            )
        else:
            self.state = "ready"
            self.jet_id.waypoint_id = self.id
        return True

    # ---------------------------
    # --------- Hooks ---------
    # ---------------------------
    def _plan_finished(self, plan_log):
        """
        Handle the plan finished event

        Args:
            plan_log (cx.tower.plan.log): Plan log record

        Returns:
            bool: True if event was handled
        """
        self.ensure_one()
        if plan_log.plan_status == 0:
            # Successfully finished the plan

            # Set the waypoint as the current waypoint
            # when successfully preparing or arriving
            if self.state in ["preparing", "arriving"]:
                self.jet_id.waypoint_id = self.id
            elif self.state == "deleting":
                self.jet_id.waypoint_id = False

            elif self.state == "leaving":
                # Arrive at the destination waypoint
                destination_waypoint = self.jet_id.waypoint_ids.filtered(
                    lambda w: w.state == "arriving"
                )
                if destination_waypoint:
                    destination_waypoint.arrive()

            # Set the waypoint state to ready (except for deleting state)
            if self.state != "deleting":
                self.state = "ready"
            return True

        # Failed to finish the plan
        # - set the waypoint state to error
        # - don't change the current waypoint
        self.state = "error"
        return True

    # ------------------------------------
    # --------- Variable Values ---------
    # ------------------------------------
    def _save_variable_values(self):
        """
        Save current jet variable values to the waypoint.
        Only jet-specific values are saved (not template/server/global values).

        Returns:
            bool: True if values were saved
        """
        self.ensure_one()

        # Get all variable values that belong to this jet specifically
        # (not template/server/global values)
        # Use variable_value_ids field from variable mixin
        jet_variable_values = self.jet_id.variable_value_ids

        # Build dictionary mapping variable_reference to value_char
        variable_values_dict = {}
        for var_value in jet_variable_values:
            variable_values_dict[var_value.variable_reference] = (
                var_value.value_char or ""
            )

        # Save to waypoint's variable_values field
        self.write({"variable_values": variable_values_dict})
        return True

    def _restore_variable_values(self):
        """
        Restore variable values from the waypoint to the jet.
        - Removes all variable values that are not saved in the waypoint

        Returns:
            bool: True if values were restored
        """
        self.ensure_one()
        if not self.variable_values:
            # Remove all jet variable values if waypoint has no saved values
            self.jet_id.variable_value_ids.unlink()
            return True

        # Get all current jet variable values
        current_jet_values = self.jet_id.variable_value_ids
        saved_references = set(self.variable_values.keys())

        # Remove variable values that are not in the saved waypoint values
        values_to_remove = current_jet_values.filtered(
            lambda v: v.variable_reference not in saved_references
        )
        if values_to_remove:
            values_to_remove.unlink()

        # Restore each variable value from the saved dictionary
        # Variable mixin handles checking if value is the same
        for variable_reference, saved_value in self.variable_values.items():
            self.jet_id.set_variable_value(variable_reference, saved_value)

        return True
