# Testing file for TREC's REC Ride Control Computer
    # Made by Jackson Justus (jackjust@bu.edu)

import unittest
from unittest.mock import MagicMock, PropertyMock, patch
from ridecontrolcomputer import RideControlComputer, State
from Backend.iocontroller import HardwareIOController, WebIOController
from Backend.states import *

class TestRideControlComputer(unittest.TestCase):
    
    def setUp(self):
        # Create an instance using the web IO controller and initialize it.
        self.rcc = RideControlComputer(useWebIOController=True)
        self.rcc.initialize()
        # Replace I/O methods with mocks to simulate input conditions.
        self.rcc.io.read_estop = MagicMock(return_value=False)
        self.rcc.io.read_stop = MagicMock(return_value=False)
        self.rcc.io.read_ride_on_off = MagicMock(return_value=False)
        self.rcc.io.read_restart = MagicMock(return_value=False)
        self.rcc.io.read_dispatch = MagicMock(return_value=False)
        # Ensure fault manager condition is false by default.
        self.rcc.fault_manager.faultRequiresEStop = False

    def test_initial_values_after_initialization(self):
        # Verify that initialization properly sets key variables.
        self.assertTrue(self.rcc.initialized)
        self.assertIsInstance(self.rcc.state, OffState)
        self.assertIsNotNone(self.rcc.io)
        self.assertIsNotNone(self.rcc.rmc)

    def test_start_without_initialization(self):
        # Create a new instance without calling initialize and ensure start() fails.
        rcc_uninit = RideControlComputer(useWebIOController=True)
        with self.assertRaises(Exception) as context:
            rcc_uninit.start()
        self.assertIn("RCC Hasn\'t been initalized", str(context.exception))

    def test_is_estop_active(self):
        # Test that is_estop_active returns True when either condition is true.
        self.rcc.io.read_estop.return_value = True
        self.assertTrue(self.rcc.is_estop_active())
        
        self.rcc.io.read_estop.return_value = False
        self.rcc.fault_manager.faultRequiresEStop = True
        self.assertTrue(self.rcc.is_estop_active())
        
        self.rcc.fault_manager.faultRequiresEStop = False
        self.assertFalse(self.rcc.is_estop_active())

    def test_estop_condition_sets_state(self):
        # Simulate an ESTOP input and check that the state becomes ESTOPPED.
        self.rcc.io.read_estop.return_value = True
        self.rcc.state = IdleState()
        self.rcc.update()
        self.assertIsInstance(self.rcc.state, EstoppedState)

    def test_stop_input_sets_idle(self):
        self.rcc.state = RunningState()

        # Test assumes estop conditions don't exist
        self.rcc.is_estop_active = MagicMock()
        self.rcc.is_estop_active.return_value = False

        self.rcc.io.stop_button.when_activated()
        self.rcc.update()
        self.assertIsInstance(self.rcc.state, StoppingState)

        self.rcc.create_event(RideFinishedHoming())

        self.rcc.update()
        self.assertIsInstance(self.rcc.state, IdleState)

    def test_reset_logic_from_estopped(self):
        # From ESTOPPED, a Reset should transition to RESETTING.
        self.rcc.state = EstoppedState()

        # Test assumes estop conditions don't exist
        self.rcc.is_estop_active = MagicMock()
        self.rcc.is_estop_active.return_value = False

        self.rcc.io.reset_button.when_activated()
        self.rcc.update()
        self.assertIsInstance(self.rcc.state, ResettingState)

    def test_reset_logic_to_idle(self):
        # From RESETTING, when Reset is no longer active, the state should go to IDLE.
        self.rcc.state = ResettingState()
        self.rcc.state._on_enter()

        # Test assumes estop conditions don't exist
        self.rcc.is_estop_active = MagicMock()
        self.rcc.is_estop_active.return_value = False

        self.rcc.update()
        time.sleep(2.1)
        self.rcc.update()
        self.assertIsInstance(self.rcc.state, IdleState)


    def test_ride_off_transitions_idle(self):
        # In OFF, if RideOff input is true, the state should transition to Idle.
        self.rcc.state = OffState()

        # Test assumes estop conditions don't exist
        self.rcc.is_estop_active = MagicMock()
        self.rcc.is_estop_active.return_value = False

        self.rcc.io.ride_onoff_button.when_activated()
        self.rcc.update()
        self.rcc.update()
        self.rcc.update()
        self.assertIsInstance(self.rcc.state, IdleState)


    def test_ride_off_transitions_to_off(self):
        # In IDLE, if RideOff input is true, the state should transition to OFF.
        self.rcc.state = IdleState()

        # Test assumes estop conditions don't exist
        self.rcc.is_estop_active = MagicMock()
        self.rcc.is_estop_active.return_value = False

        self.rcc.io.ride_onoff_button.when_deactivated()

        self.rcc.update()
        self.assertIsInstance(self.rcc.state, OffState)

    def test_ride_off_transitions_to_off_when_power_off(self):
        # The state should transition to OFF after resetting if power is set to the off pos.
        self.rcc.io.ride_onoff_button.when_deactivated()

        self.rcc.state = IdleState()

        # Test assumes estop conditions don't exist
        self.rcc.is_estop_active = MagicMock()
        self.rcc.is_estop_active.return_value = False

        self.rcc.update()
        self.assertIsInstance(self.rcc.state, OffState)

    def test_dispatch_transitions_to_running(self):
        # In IDLE, if Dispatch input is true, the state should transition to RUNNING.
        self.rcc.state = IdleState()
        
        # Test assumes estop conditions don't exist
        self.rcc.is_estop_active = MagicMock()
        self.rcc.is_estop_active.return_value = False

        self.rcc.io.dispatch_button.when_activated()
        self.rcc.update()
        self.assertIsInstance(self.rcc.state, RunningState)

    def test_latched_estop_in_state_transition(self):
        self.rcc.io.estop_button.pin.drive_high()
        self.rcc.io.ride_onoff_button.pin.drive_high()
        self.assertIsInstance(self.rcc.state, EstoppedState)

    def test_idle_state_is_sustained(self):
        # Test assumes estop conditions don't exist
        self.rcc.is_estop_active = MagicMock()
        self.rcc.is_estop_active.return_value = False

        self.rcc.io.ride_onoff_button.pin.drive_high()
        self.assertIsInstance(self.rcc.state, IdleState)
        self.rcc.update()
        self.assertIsInstance(self.rcc.state, IdleState)

    def test_fault_manager_raises_estop(self):
        self.rcc.state = RunningState()
        self.rcc.fault_manager.faultRequiresEStop = True
        self.rcc.update()
        self.assertIsInstance(self.rcc.state, EstoppedState)

    def test_motor_stops_during_estop(self):
        # Set state to Running and assume motor is running
        self.rcc.state = RunningState()
        self.rcc.rmc.is_running = True
        self.rcc.rmc.start_cycle = MagicMock(return_value="Instruction1")
        self.rcc.rmc.update = MagicMock(return_value="Instruction1")
        self.rcc.io.send_motor_command = MagicMock()
        self.rcc.io.stop_motor = MagicMock()

        # Simulate ESTOP activation
        self.rcc.io.read_estop.return_value = True
        self.rcc.update()

        # Ensure state is Estopped and motor timeout executed
        self.assertIsInstance(self.rcc.state, EstoppedState)
        self.rcc.io.stop_motor.assert_not_called()
        self.rcc.io.send_motor_command.assert_not_called()
        

    # def test_io_actions_on_estopped(self):
        # TODO: Update with expected behavior
        # When in ESTOPPED state, the system should call terminate_power() on the I/O controller.
        # self.rcc.state = EstoppedState()
        # self.rcc.io.terminate_power = MagicMock()
        # self.rcc.update()
        # self.rcc.io.terminate_power.assert_called_once()
        # pass

    # def test_io_actions_on_running(self):
        # TODO: Update with expected behavior
        # In RUNNING state, enable_motors() should be called and run_ride() executed.
        # self.rcc.state = RunningState()
        # self.rcc.io.enable_motors = MagicMock()
        # self.rcc.run_ride = MagicMock()
        # self.rcc.update()
        # self.rcc.io.enable_motors.assert_called_once()
        # self.rcc.run_ride.assert_called_once()
        # pass

    # def test_io_actions_on_idle(self):
        # TODO: Update with expected behavior
        # In IDLE state, disable_motors() should be called.
        # self.rcc.state = IdleState()
        # self.rcc.io.disable_motors = MagicMock()
        # self.rcc.update()
        # self.rcc.io.disable_motors.assert_called_once()
        # pass

if __name__ == "__main__":
    unittest.main()