import sys
import numpy as np
import pyvisa
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout,
    QLabel, QComboBox, QLineEdit, QHBoxLayout, QFileDialog
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class TekScopeGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tektronix MSO64 Control Panel")
        self.scope = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Trigger Settings
        trigger_layout = QHBoxLayout()
        self.trigger_source = QComboBox()
        self.trigger_source.addItems(["CH1", "CH2", "D0", "D1"])
        self.trigger_level = QLineEdit("1.00")
        trigger_layout.addWidget(QLabel("Trigger Source:"))
        trigger_layout.addWidget(self.trigger_source)
        trigger_layout.addWidget(QLabel("Level (V):"))
        trigger_layout.addWidget(self.trigger_level)

        # Buttons
        self.connect_button = QPushButton("Connect to Scope")
        self.capture_button = QPushButton("Run Capture")
        self.save_button = QPushButton("Save CSV")

        self.connect_button.clicked.connect(self.connect_scope)
        self.capture_button.clicked.connect(self.run_capture)
        self.save_button.clicked.connect(self.save_csv)

        # Matplotlib Plot
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)

        # Add widgets to layout
        layout.addLayout(trigger_layout)
        layout.addWidget(self.connect_button)
        layout.addWidget(self.capture_button)
        layout.addWidget(self.save_button)
        layout.addWidget(self.canvas)

        self.setLayout(layout)

    def connect_scope(self):
        rm = pyvisa.ResourceManager()
        try:
            instruments = rm.list_resources()
            self.scope = rm.open_resource(instruments[0])  # Use first found
            idn = self.scope.query("*IDN?")
            print(f"Connected to: {idn}")
        except Exception as e:
            print(f"Connection failed: {e}")

    def run_capture(self):
        if not self.scope:
            return

        source = self.trigger_source.currentText()
        level = self.trigger_level.text()

        self.scope.write("*CLS")
        self.scope.write("ACQUIRE:STOPAFTER SEQUENCE")
        self.scope.write("TRIGGER:A:TYPE EDGE")
        self.scope.write(f"TRIGGER:A:EDGE:SOURCE {source}")
        self.scope.write(f"TRIGGER:A:LEVEL:{source} {level}")

        self.scope.write("DATA:SOURCE CH1")
        self.scope.write("DATA:ENC ASCII")
        self.scope.write("DATA:START 1")
        self.scope.write("DATA:STOP 1000")

        self.scope.write("ACQUIRE:STATE RUN")
        while self.scope.query("BUSY?").strip() == '1':
            pass

        data = self.scope.query("CURVE?")
        self.waveform = np.array([float(x) for x in data.split(',')])

        # Plot
        self.ax.clear()
        self.ax.plot(self.waveform)
        self.ax.set_title("Captured Waveform - CH1")
        self.ax.set_xlabel("Sample")
        self.ax.set_ylabel("Voltage (V)")
        self.canvas.draw()

    def save_csv(self):
        if hasattr(self, 'waveform'):
            filename, _ = QFileDialog.getSaveFileName(self, "Save CSV", "waveform.csv", "CSV files (*.csv)")
            if filename:
                np.savetxt(filename, self.waveform, delimiter=',')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = TekScopeGUI()
    gui.show()
    sys.exit(app.exec_())
