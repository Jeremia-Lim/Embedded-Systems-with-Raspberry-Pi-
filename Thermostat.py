

#
# Thermostat - Completed CS-350 Final Project version
# Uses two physical buttons (green + red) to provide three actions:
#   - Cycle thermostat state (off/heat/cool)
#   - Increase setpoint by 1°F
#   - Decrease setpoint by 1°F (via long-press on red button)
#


from time import sleep
from datetime import datetime


from statemachine import StateMachine, State


import board
import adafruit_ahtx0


# import board - already imported above for I2C connectivity
import digitalio
import adafruit_character_lcd.character_lcd as characterlcd


import serial


from gpiozero import Button, PWMLED


from threading import Thread
from math import floor


# DEBUG flag - boolean value to indicate whether or not to print
# status messages on the console of the program
DEBUG = True


# ---------------- I2C / SENSOR ----------------
i2c = board.I2C()


# Initialize our Temperature and Humidity sensor
thSensor = adafruit_ahtx0.AHTx0(i2c)


# ---------------- SERIAL PORT -----------------
# Initialize our serial connection (/dev/ttyS0, 115200 baud)
ser = serial.Serial(
        port='/dev/ttyS0',  # This would be /dev/ttyAMA0 prior to Raspberry Pi 3
        baudrate = 115200,  # bits per second
        parity=serial.PARITY_NONE,      # Disable parity
        stopbits=serial.STOPBITS_ONE,   # One stop bit
        bytesize=serial.EIGHTBITS,      # 8-bit bytes 
        timeout=1          # 1-second timeout
)


# ---------------- LED SETUP -------------------
# Our two LEDs, utilizing GPIO 18 (red) and GPIO 23 (blue)
redLight = PWMLED(18)
blueLight = PWMLED(23)




# ======================================================================
#  ManagedDisplay - Class intended to manage the 16x2 Display
# ======================================================================
class ManagedDisplay():
    """
    Manages the 16x2 character LCD using the same wiring pattern as
    the course labs.
    """
    def __init__(self):
        # Setup the six GPIO lines to communicate with the display.
        self.lcd_rs = digitalio.DigitalInOut(board.D17)
        self.lcd_en = digitalio.DigitalInOut(board.D27)
        self.lcd_d4 = digitalio.DigitalInOut(board.D5)
        self.lcd_d5 = digitalio.DigitalInOut(board.D6)
        self.lcd_d6 = digitalio.DigitalInOut(board.D13)
        self.lcd_d7 = digitalio.DigitalInOut(board.D26)


        # Character LCD size
        self.lcd_columns = 16
        self.lcd_rows = 2 


        # Initialise the lcd class
        self.lcd = characterlcd.Character_LCD_Mono(
            self.lcd_rs, self.lcd_en, 
            self.lcd_d4, self.lcd_d5, self.lcd_d6, self.lcd_d7, 
            self.lcd_columns, self.lcd_rows
        )


        # Wipe LCD screen before we start
        self.lcd.clear()


    def cleanupDisplay(self):
        # Clear the LCD first - otherwise we won't be able to update it.
        self.lcd.clear()
        self.lcd_rs.deinit()
        self.lcd_en.deinit()
        self.lcd_d4.deinit()
        self.lcd_d5.deinit()
        self.lcd_d6.deinit()
        self.lcd_d7.deinit()
        
    def clear(self):
        self.lcd.clear()


    def updateScreen(self, message: str):
        """
        Convenience method used to update the message.
        message should be a 2-line string separated by '\n'.
        """
        self.lcd.clear()
        self.lcd.message = message




# Initialize our display
screen = ManagedDisplay()




# ======================================================================
#  TemperatureMachine - StateMachine implementation class
# ======================================================================
class TemperatureMachine(StateMachine):
    """
    A state machine designed to manage our thermostat.


    States:
      - off  : both LEDs off
      - heat : red LED (fade vs solid depending on temp vs setPoint)
      - cool : blue LED (fade vs solid depending on temp vs setPoint)
    """


    # Define the three states for our machine.
    off = State(initial=True)
    heat = State()
    cool = State()


    # Default temperature setPoint is 72 degrees Fahrenheit
    setPoint = 72


    # cycle - event to transition between the states of the thermostat
    cycle = (
        off.to(heat) |
        heat.to(cool) |
        cool.to(off)
    )


    # ---------------- ENTER / EXIT STATE ACTIONS ----------------


    def on_enter_heat(self):
        """
        Action performed when the state machine transitions into 'heat'.
        """
        # Update the indicator lights for the new state
        self.updateLights()


        if DEBUG:
            print("* Changing state to heat")


    def on_exit_heat(self):
        """
        Action performed when the state machine transitions out of 'heat'.
        """
        # Turn off red when exiting heat
        redLight.off()


    def on_enter_cool(self):
        """
        Action performed when the state machine transitions into 'cool'.
        """
        # Update the indicator lights for the new state
        self.updateLights()


        if DEBUG:
            print("* Changing state to cool")
    
    def on_exit_cool(self):
        """
        Action performed when the state machine transitions out of 'cool'.
        """
        # Turn off blue when exiting cool
        blueLight.off()


    def on_enter_off(self):
        """
        Action performed when the state machine transitions into 'off'.
        """
        # Turn off both LEDs when in the off state
        redLight.off()
        blueLight.off()


        if DEBUG:
            print("* Changing state to off")
    
    # ---------------- BUTTON HANDLERS ----------------


    def processTempStateButton(self):
        """
        Utility method used to send events to the state machine.
        Triggered by the green button to cycle thermostat state.
        """
        if DEBUG:
            print("Cycling Temperature State")
        # Change the state of the thermostat.
        self.cycle()


    def processTempIncButton(self):
        """
        Utility method used to increase the setPoint by 1°F.
        Triggered by short press on the red button.
        """
        if DEBUG:
            print("Increasing Set Point")


        # Increase setPoint and update lights
        self.setPoint += 1
        self.updateLights()


    def processTempDecButton(self):
        """
        Utility method used to decrease the setPoint by 1°F.
        Triggered by long press on the red button (since only 2 buttons exist).
        """
        if DEBUG:
            print("Decreasing Set Point")


        # Decrease setPoint and update lights
        self.setPoint -= 1
        self.updateLights()


    # ---------------- LED UPDATE LOGIC ----------------


    def updateLights(self):
        """
        Update the LED indicators based on:
          - current state (off / heat / cool)
          - temperature vs setPoint
        Behavior:
          - OFF: both off
          - HEAT: 
              temp < setPoint  -> red fades
              temp >= setPoint -> red solid
          - COOL:
              temp > setPoint  -> blue fades
              temp <= setPoint -> blue solid
        """
        # Make sure we are comparing temperatures in the correct scale
        temp = floor(self.getFahrenheit())
        redLight.off()
        blueLight.off()
    
        # Verify values for debug purposes
        if DEBUG:
            print(f"State: {self.current_state.id}")
            print(f"SetPoint: {self.setPoint}")
            print(f"Temp: {temp}")


        # Heat mode: use red LED
        if self.current_state == self.heat:
            if temp < self.setPoint:
                # Below setpoint: fade red
                redLight.pulse()
            else:
                # At or above setpoint: solid red
                redLight.on()


        # Cool mode: use blue LED
        elif self.current_state == self.cool:
            if temp > self.setPoint:
                # Above setpoint: fade blue
                blueLight.pulse()
            else:
                # At or below setpoint: solid blue
                blueLight.on()


        # Off mode: both off (already handled above)


    # ---------------- TEMPERATURE READING ----------------


    def getFahrenheit(self):
        """
        Get the temperature in degrees Fahrenheit.
        """
        t = thSensor.temperature
        return (((9/5) * t) + 32)
    
    # ---------------- UART OUTPUT STRING ----------------


    def setupSerialOutput(self):
        """
        Configure output string for the Thermostat Server.
        Returns a comma-delimited string:
            state,currentTempF,setPointF
        """
        temp = floor(self.getFahrenheit())
        output = f"{self.current_state.id},{temp},{self.setPoint}"
        return output
    
    # Continue display output
    endDisplay = False


    # ---------------- LCD MANAGEMENT THREAD ----------------


    def manageMyDisplay(self):
        """
        Manage the LCD display.
        Line 1: date + time
        Line 2: alternates between current temp and state/setPoint.
        Also updates the lights and sends UART output every 30 seconds.
        """
        counter = 1
        altCounter = 1
        while not self.endDisplay:
            # Only display if the DEBUG flag is set
            if DEBUG:
                print("Processing Display Info...")
    
            # Grab the current time        
            current_time = datetime.now()
    
            # Setup display line 1: current date and time
            lcd_line_1 = current_time.strftime("%m/%d %H:%M")


            # Setup Display Line 2
            if altCounter < 6:
                # Show current temperature in degrees Fahrenheit
                temp_f = floor(self.getFahrenheit())
                lcd_line_2 = f"\nTemp:{temp_f}F"
                altCounter = altCounter + 1
            else:
                # Show current state and setpoint in degrees Fahrenheit
                lcd_line_2 = f"\n{self.current_state.id}:{self.setPoint}F"
                altCounter = altCounter + 1
                if altCounter >= 11:
                    # Run the routine to update the lights every 10 seconds
                    # to keep operations smooth
                    self.updateLights()
                    altCounter = 1
    
            # Update Display
            screen.updateScreen(lcd_line_1 + lcd_line_2)
    
            # Update server every 30 seconds
            if DEBUG:
               print(f"Counter: {counter}")
            if (counter % 30) == 0:
                # Send current state information to the TemperatureServer
                # over the Serial Port (UART).
                ser.write((self.setupSerialOutput() + "\n").encode())
                counter = 1
            else:
                counter = counter + 1
            sleep(1)


        # Cleanup display
        screen.cleanupDisplay()


    # ---------------- START DISPLAY THREAD ----------------


    def run(self):
        myThread = Thread(target=self.manageMyDisplay)
        myThread.start()




# ================== Setup our State Machine ==================
tsm = TemperatureMachine()
tsm.run()




# ================== BUTTON CONFIGURATION ==================


##
## Green button on GPIO 24:
##   - Short press cycles the thermostat state (off → heat → cool → off)
##
greenButton = Button(24)
greenButton.when_pressed = tsm.processTempStateButton


##
## Red button on GPIO 25:
##   - Short press  -> increase setPoint by 1°F
##   - Long press   -> decrease setPoint by 1°F
## This lets us support all three logical actions with only two physical buttons.
##
redButton = Button(25, hold_time=1.0)
redButton.when_pressed = tsm.processTempIncButton
redButton.when_held    = tsm.processTempDecButton


##
## Blue button on GPIO 12:
##   - Defined for completeness; you do NOT need to wire this
##     if you only have two buttons. It will simply never be pressed.
##
blueButton = Button(12)
# Optional if you later add a third button:
# blueButton.when_pressed = tsm.processTempDecButton




# ================== MAIN LOOP ==================


repeat = True


##
## Repeat until the user creates a keyboard interrupt (CTRL-C)
##
while repeat:
    try:
        # Most of the work happens in the state machine's thread and in
        # button callbacks; this loop just keeps the program running.
        sleep(30)


    except KeyboardInterrupt:
        # Catch the keyboard interrupt (CTRL-C) and exit cleanly
        # gpiozero will handle GPIO cleanup automatically.
        print("Cleaning up. Exiting...")


        # Stop the loop
        repeat = False
        
        # Close down the display
        tsm.endDisplay = True
        sleep(1)




