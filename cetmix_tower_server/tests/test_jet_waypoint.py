# Copyright (C) 2024 Cetmix OÜ
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from .common_jets import TestTowerJetsCommon


class TestTowerJetWaypoint(TestTowerJetsCommon):
    """
    Test the Jet Waypoint model functionality
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create variables for testing
        cls.variable_test_1 = cls.Variable.create(
            {
                "name": "Test Variable 1",
                "reference": "test_var_1",
            }
        )
        cls.variable_test_2 = cls.Variable.create(
            {
                "name": "Test Variable 2",
                "reference": "test_var_2",
            }
        )
        cls.variable_test_3 = cls.Variable.create(
            {
                "name": "Test Variable 3",
                "reference": "test_var_3",
            }
        )
        # waypoint_template and waypoint are now inherited from TestTowerJetsCommon

    def test_save_variable_values_empty(self):
        """
        Test _save_variable_values when jet has no variable values
        """
        # Ensure jet has no variable values
        self.jet_test.variable_value_ids.unlink()

        # Save variable values
        result = self.waypoint._save_variable_values()

        # Should return True
        self.assertTrue(result, "Should return True when saving values")

        # Waypoint should have empty variable_values (or False, which is equivalent)
        variable_values = self.waypoint.variable_values or {}
        self.assertEqual(
            variable_values,
            {},
            "Variable values should be empty dict when jet has no values",
        )

    def test_save_variable_values_with_values(self):
        """
        Test _save_variable_values when jet has variable values
        """
        # Create variable values for the jet
        self.VariableValue.create(
            {
                "variable_id": self.variable_test_1.id,
                "value_char": "value_1",
                "jet_id": self.jet_test.id,
            }
        )
        self.VariableValue.create(
            {
                "variable_id": self.variable_test_2.id,
                "value_char": "value_2",
                "jet_id": self.jet_test.id,
            }
        )

        # Save variable values
        result = self.waypoint._save_variable_values()

        # Should return True
        self.assertTrue(result, "Should return True when saving values")

        # Waypoint should have saved variable values
        self.assertEqual(
            self.waypoint.variable_values,
            {"test_var_1": "value_1", "test_var_2": "value_2"},
            "Variable values should be saved correctly",
        )

    def test_save_variable_values_with_empty_string(self):
        """
        Test _save_variable_values when variable value is empty string
        """
        # Create variable value with empty string
        self.VariableValue.create(
            {
                "variable_id": self.variable_test_1.id,
                "value_char": "",
                "jet_id": self.jet_test.id,
            }
        )

        # Save variable values
        self.waypoint._save_variable_values()

        # Waypoint should have saved empty string value
        self.assertEqual(
            self.waypoint.variable_values,
            {"test_var_1": ""},
            "Empty string values should be saved",
        )

    def test_save_variable_values_only_jet_values(self):
        """
        Test _save_variable_values only saves jet-specific values,
        not template/server/global values
        """
        # Create jet-specific variable value
        self.VariableValue.create(
            {
                "variable_id": self.variable_test_1.id,
                "value_char": "jet_value",
                "jet_id": self.jet_test.id,
            }
        )

        # Create template variable value (should not be saved)
        self.VariableValue.create(
            {
                "variable_id": self.variable_test_2.id,
                "value_char": "template_value",
                "jet_template_id": self.jet_template_test.id,
            }
        )

        # Save variable values
        self.waypoint._save_variable_values()

        # Waypoint should only have jet-specific value
        self.assertEqual(
            self.waypoint.variable_values,
            {"test_var_1": "jet_value"},
            "Should only save jet-specific values",
        )
        self.assertNotIn(
            "test_var_2",
            self.waypoint.variable_values,
            "Should not save template values",
        )

    def test_restore_variable_values_empty(self):
        """
        Test _restore_variable_values when waypoint has no saved values
        """
        # Create some variable values in jet
        self.VariableValue.create(
            {
                "variable_id": self.variable_test_1.id,
                "value_char": "existing_value",
                "jet_id": self.jet_test.id,
            }
        )

        # Set waypoint variable_values to empty
        self.waypoint.variable_values = {}

        # Restore variable values
        result = self.waypoint._restore_variable_values()

        # Should return True
        self.assertTrue(result, "Should return True when restoring values")

        # Jet should have no variable values
        self.assertEqual(
            len(self.jet_test.variable_value_ids),
            0,
            "All jet variable values should be removed when waypoint is empty",
        )

    def test_restore_variable_values_basic(self):
        """
        Test _restore_variable_values restores values correctly
        """
        # Set waypoint variable values
        self.waypoint.variable_values = {
            "test_var_1": "restored_value_1",
            "test_var_2": "restored_value_2",
        }

        # Restore variable values
        result = self.waypoint._restore_variable_values()

        # Should return True
        self.assertTrue(result, "Should return True when restoring values")

        # Check values were restored
        self.assertEqual(
            self.jet_test.get_variable_value("test_var_1", no_fallback=True),
            "restored_value_1",
            "Variable 1 should be restored",
        )
        self.assertEqual(
            self.jet_test.get_variable_value("test_var_2", no_fallback=True),
            "restored_value_2",
            "Variable 2 should be restored",
        )

    def test_restore_variable_values_removes_unsaved(self):
        """
        Test _restore_variable_values removes variable values not in waypoint
        """
        # Create variable values in jet
        self.VariableValue.create(
            {
                "variable_id": self.variable_test_1.id,
                "value_char": "value_1",
                "jet_id": self.jet_test.id,
            }
        )
        self.VariableValue.create(
            {
                "variable_id": self.variable_test_2.id,
                "value_char": "value_2",
                "jet_id": self.jet_test.id,
            }
        )
        self.VariableValue.create(
            {
                "variable_id": self.variable_test_3.id,
                "value_char": "value_3",
                "jet_id": self.jet_test.id,
            }
        )

        # Set waypoint to only have variable 1 and 2
        self.waypoint.variable_values = {
            "test_var_1": "value_1",
            "test_var_2": "value_2",
        }

        # Restore variable values
        self.waypoint._restore_variable_values()

        # Variable 3 should be removed
        self.assertIsNone(
            self.jet_test.get_variable_value("test_var_3", no_fallback=True),
            "Variable 3 should be removed",
        )

        # Variables 1 and 2 should still exist
        self.assertEqual(
            self.jet_test.get_variable_value("test_var_1", no_fallback=True),
            "value_1",
            "Variable 1 should still exist",
        )
        self.assertEqual(
            self.jet_test.get_variable_value("test_var_2", no_fallback=True),
            "value_2",
            "Variable 2 should still exist",
        )

    def test_restore_variable_values_updates_existing(self):
        """
        Test _restore_variable_values updates existing variable values
        """
        # Create variable value in jet
        self.VariableValue.create(
            {
                "variable_id": self.variable_test_1.id,
                "value_char": "old_value",
                "jet_id": self.jet_test.id,
            }
        )

        # Set waypoint with new value
        self.waypoint.variable_values = {"test_var_1": "new_value"}

        # Restore variable values
        self.waypoint._restore_variable_values()

        # Value should be updated
        self.assertEqual(
            self.jet_test.get_variable_value("test_var_1", no_fallback=True),
            "new_value",
            "Variable value should be updated",
        )

    def test_save_and_restore_roundtrip(self):
        """
        Test saving and restoring variable values in a roundtrip
        """
        # Create initial variable values
        self.VariableValue.create(
            {
                "variable_id": self.variable_test_1.id,
                "value_char": "initial_value_1",
                "jet_id": self.jet_test.id,
            }
        )
        self.VariableValue.create(
            {
                "variable_id": self.variable_test_2.id,
                "value_char": "initial_value_2",
                "jet_id": self.jet_test.id,
            }
        )

        # Save variable values
        self.waypoint._save_variable_values()

        # Modify jet values
        self.jet_test.set_variable_value("test_var_1", "modified_value_1")
        self.jet_test.set_variable_value("test_var_2", "modified_value_2")
        self.VariableValue.create(
            {
                "variable_id": self.variable_test_3.id,
                "value_char": "new_value",
                "jet_id": self.jet_test.id,
            }
        )

        # Restore variable values
        self.waypoint._restore_variable_values()

        # Values should be restored to original
        self.assertEqual(
            self.jet_test.get_variable_value("test_var_1", no_fallback=True),
            "initial_value_1",
            "Variable 1 should be restored to original value",
        )
        self.assertEqual(
            self.jet_test.get_variable_value("test_var_2", no_fallback=True),
            "initial_value_2",
            "Variable 2 should be restored to original value",
        )
        # Variable 3 should be removed (not in saved waypoint)
        self.assertIsNone(
            self.jet_test.get_variable_value("test_var_3", no_fallback=True),
            "Variable 3 should be removed",
        )
