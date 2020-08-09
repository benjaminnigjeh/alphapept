from PyQt5.QtCore import QUrl, QSize, QThread, pyqtSignal, Qt, QAbstractTableModel, QCoreApplication
from PyQt5.QtWidgets import QTableWidgetItem, QTableView, QTabWidget, QPlainTextEdit, QProgressBar, QSpinBox, QGroupBox, QCheckBox, QDoubleSpinBox, QTreeWidget, QTreeWidgetItem, QComboBox, QAbstractScrollArea, QPushButton, QTableWidget, QStackedWidget, QWidget, QMainWindow, QApplication, QStyleFactory, QHBoxLayout, QVBoxLayout, QLabel, QSpacerItem, QSizePolicy
from PyQt5.QtGui import QIcon, QPixmap, QMovie
from PyQt5.QtCore import pyqtSlot

import sys
import os

from functools import partial

from .stylesheets import (
	big_font,
	version_font,
	logo_font,
	progress_style,
	busy_style,
	progress_style_1,
	progress_style_2,
	progress_style_3,
	progress_style_4,
)

from alphapept.runner import run_alphapept

import yaml
import numpy as np
from time import time, sleep
import psutil
from qroundprogressbar import QRoundProgressBar
import logging
import pandas as pd
import qdarkstyle
import os


dark_stylesheet = qdarkstyle.load_stylesheet_pyqt5()

_this_file = os.path.abspath(__file__)
_this_directory = os.path.dirname(_this_file)

SETTINGS_TEMPLATE_PATH = os.path.join(_this_directory,  "settings_template.yaml")
LOGO_PATH = os.path.join(_this_directory, "img", "logo_200px.png")
ICON_PATH = os.path.join(_this_directory, "img", "logo.ico")
BUSY_INDICATOR_PATH = os.path.join(_this_directory, "img", "busy_indicator.gif")

# Get Version

VERSION_NO = "0.2.4-dev0"

URL_DOCUMENTATION = "https://mannlabs.github.io/alphapept/"
URL_ISSUE = "https://github.com/MannLabs/alphapept/issues"
URL_CONTRIBUTE = "https://github.com/MannLabs/alphapept/blob/master/CONTRIBUTING.md"

if not os.path.isfile(ICON_PATH):
	raise FileNotFoundError('Logo not found - Path {}'.format(ICON_PATH))

if not os.path.isfile(BUSY_INDICATOR_PATH):
	raise FileNotFoundError('Busy Indicator - Path {}'.format(BUSY_INDICATOR_PATH))

def cancel_dialogs():
	dialogs = [_ for _ in _dialogs]
	for dialog in dialogs:
		if isinstance(dialog, ProgressDialog):
			dialog.cancel()
		else:
			dialog.close()
	QCoreApplication.instance().processEvents()  # just in case...

class FileSelector(QWidget):

	def __init__(self, header):
		super().__init__()
		self.title = 'FileSelection'
		self.left = 0
		self.top = 0
		self.width = 600
		self.height = 200
		self.files = []
		self.header = header
		self.setAcceptDrops(True)
		self.initUI()

	def initUI(self):
		self.setWindowTitle(self.title)
		self.setGeometry(self.left, self.top, self.width, self.height)
		self.createTable()

		# Add box layout, add table to box layout and add box layout to widget
		self.layout = QVBoxLayout()
		self.layout.setContentsMargins(0,0,0,0)
		self.layout.setSpacing(0)

		self.layout.addWidget(self.tableWidget)
		self.setLayout(self.layout)

		# Show widget
		self.show()

	def createTable(self):
	   # Create table
		HEADER_LABELS = self.header
		HEADER_LABELS.append("Remove")

		self.tableWidget = QTableWidget()
		self.tableWidget.setRowCount(0)
		self.tableWidget.setColumnCount(len(HEADER_LABELS))
		self.tableWidget.setHorizontalHeaderLabels(HEADER_LABELS)
		self.tableWidget.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
		self.tableWidget.doubleClicked.connect(self.on_click)

	@pyqtSlot()
	def on_click(self):
		for currentQTableWidgetItem in self.tableWidget.selectedItems():
			print(currentQTableWidgetItem.row(), currentQTableWidgetItem.column(), currentQTableWidgetItem.text())

	def dragMoveEvent(self, event):
		event.accept()

	def path_from_drop(self, event):
		url = event.mimeData().urls()[0]
		path = url.toLocalFile()
		return path

	def drop_has_valid_url(self, event):
		if not event.mimeData().hasUrls():
			return False
		else:
			return True

	def dragEnterEvent(self, event):
		if self.drop_has_valid_url(event):
			event.accept()
		else:
			event.ignore()

	def dropEvent(self, event):
		""" Loads  when dropped into the scene """
		path = self.path_from_drop(event)
		logging.info("Dropped file {}.".format(path))
		self.open(path)

	def open(self, path):
		pass

	def set_files(self):
		n_files = len(self.files)
		self.tableWidget.setRowCount(n_files)
		self.remove_btns = []
		for i in range(n_files):
			self.tableWidget.setItem(i, 0, QTableWidgetItem(self.files[i]))
			btn = QPushButton('X')
			self.remove_btns.append(btn)
			self.tableWidget.setCellWidget(i, len(self.header)-1, btn)
			btn.clicked.connect(self.remove_file)

		self.tableWidget.resizeColumnsToContents()

	def remove_file(self):
		sending_button = self.sender()
		index = self.remove_btns.index(sending_button)
		del self.files[index]
		self.set_files()

	def read_table(self):
		table = []

		for row in range(self.tableWidget.rowCount()):
			entry = []
			for column in range(self.tableWidget.columnCount()-1):
				widgetItem = self.tableWidget.item(row, column)
				if (widgetItem and widgetItem.text):
					entry.append(widgetItem.text())
				else:
					entry.append(None)
			table.append(entry)

		return pd.DataFrame(table, columns = self.header[:-1])

	def set_table(self, table):
		self.remove_btns = []
		columns = table.columns
		self.tableWidget.setRowCount(len(table))
		for row in range(len(table)):
			for idx, col in enumerate(columns):
				self.tableWidget.setItem(row, idx, QTableWidgetItem(table.iloc[row, col]))
			btn = QPushButton('X')
			self.remove_btns.append(btn)
			self.tableWidget.setCellWidget(row, idx+1, btn)

		self.tableWidget.resizeColumnsToContents()

class RawFileSelector(FileSelector):
	def __init__(self, header):
		super().__init__(header)

	def open(self, path):
		path = os.path.normpath(path)

		files = self.files

		new_files = []
		if path.endswith('.d'):
			new_files.append(path)
		if path.endswith('.raw'):
			new_files.append(path)
		for dirpath, dirnames, filenames in os.walk(path):
			for dirname in [d for d in dirnames if d.endswith('.d')]: #Bruker
				new_file = os.path.join(dirpath, dirname)
				new_files.append(new_file)
			for filename in [f for f in filenames if f.lower().endswith('.raw')]: #Thermo
				new_file = os.path.join(dirpath, filename)
				new_files.append(new_file)
		for new_file in new_files:
			if new_file not in files:
				files.append(new_file)

		files.sort()
		self.files = files
		self.set_files()

class FastaFileSelector(FileSelector):
	def __init__(self, header):
		super().__init__(header)

	def open(self, path):
		path = os.path.normpath(path)
		print(path)

		files = self.files
		new_files = []
		if path.endswith('.fasta'):
			new_files.append(path)

		for dirpath, dirnames, filenames in os.walk(path):
			for filename in [f for f in filenames if f.lower().endswith('.fasta')]: #Thermo
				new_file = os.path.join(dirpath, filename)
				new_files.append(new_file)

		for new_file in new_files:
			if new_file not in files:
				files.append(new_file)

		files.sort()
		self.files = files
		self.set_files()


class pandasModel(QAbstractTableModel):

	"""
	Taken from https://learndataanalysis.org/display-pandas-dataframe-with-pyqt5-qtableview-widget/
	"""

	def __init__(self, data):
		QAbstractTableModel.__init__(self)
		self._data = data

	def rowCount(self, parent=None):
		return self._data.shape[0]

	def columnCount(self, parnet=None):
		return self._data.shape[1]

	def data(self, index, role=Qt.DisplayRole):
		if index.isValid():
			if role == Qt.DisplayRole:
				return str(self._data.iloc[index.row(), index.column()])
		return None

	def headerData(self, col, orientation, role):
		if orientation == Qt.Horizontal and role == Qt.DisplayRole:
			return self._data.columns[col]
		return None

class QTextEditLogger(logging.Handler):
	def __init__(self, parent):
		super().__init__()
		self.widget = QPlainTextEdit(parent)
		self.widget.setReadOnly(True)

	def emit(self, record):
		msg = self.format(record)
		self.widget.appendPlainText(msg)
		self.widget.verticalScrollBar().setValue(self.widget.verticalScrollBar().maximum())


class searchThread(QThread):
	"""
	Thread to run the search
	"""

	current_progress_update = pyqtSignal(float)
	global_progress_update = pyqtSignal(float)
	task_update = pyqtSignal(str)

	def __init__(self, settings):
		QThread.__init__(self)
		self.settings = settings

	def update_current_progress(self, progress):
		self.current_progress_update.emit(progress)

	def update_global_progress(self, progress):
		self.global_progress_update.emit(progress)

	def update_task(self, task):
		self.task_update.emit(task)

	def run(self):
		logging.info('Starting SearchThread')
		print(yaml.dump(self.settings, default_flow_style=False))
		run_alphapept(self.settings, callback=self.update_current_progress)
		try:
			run_alphapept(self.settings, callback=self.update_current_progress)
		except Exception as e:
			logging.error('Error occured. {}'.format(e))


class External(QThread):
	"""
	Runs a counter thread to update the system stats
	"""

	countChanged = pyqtSignal(int)

	def run(self):
		count = 0
		while True:
			count += 1
			sleep(0.5)
			self.countChanged.emit(count)
			count -= 1

class SettingsEdit(QWidget):
	def __init__(self):
		super().__init__()
		self.setAcceptDrops(True)

		self.initUI()

	def initUI(self):
		# Add box layout, add table to box layout and add box layout to widget
		self.layout = QVBoxLayout()
		self.layout.setContentsMargins(0,0,0,0)
		self.layout.setSpacing(0)

		self.treeWidget = QTreeWidget()

		self.layout.addWidget(self.treeWidget)
		self.setLayout(self.layout)

		# Show widget
		self.show()
		self.init_tree()

	def path_from_drop(self, event):
		url = event.mimeData().urls()[0]
		path = url.toLocalFile()
		base, extension = os.path.splitext(path)
		return path, extension

	def drop_has_valid_url(self, event):
		if not event.mimeData().hasUrls():
			return False
		path, extension = self.path_from_drop(event)
		if extension.lower() not in [".yaml", ".npz", ".raw", ".fasta"]:
			return False
		return True

	def dragEnterEvent(self, event):
		if self.drop_has_valid_url(event):
			event.accept()
		else:
			event.ignore()

	def dropEvent(self, event):
		""" Loads  when dropped into the scene """

		path, extension = self.path_from_drop(event)

		logging.info("Dropped file {}.".format(path))

		if extension == ".yaml":

			with open(path, "r") as settings_file:
				settings = yaml.load(settings_file, Loader=yaml.FullLoader)
			self.set_settings(settings)
			logging.info("Loaded settings from {}.".format(path))
			logging.info("THis method is not properly implemented.")
		else:
			print("Extension not found {}".format(extension))
			raise NotImplementedError

	def read_settings(self):
		settings = {}

		for category in self.categories.keys():

			settings[category] = {}
			for widget_name in self.categories[category]["widgets"].keys():

				widget = self.categories[category]["widgets"][widget_name]
				if isinstance(widget, QSpinBox):
					settings[category][widget_name] = widget.value()
				elif isinstance(widget, QDoubleSpinBox):
					settings[category][widget_name] = widget.value()
				elif isinstance(widget, QPushButton):
					settings[category][widget_name] = widget.text()
				elif isinstance(widget, QComboBox):
					settings[category][widget_name] = widget.currentText()
				elif isinstance(widget, QCheckBox):
					state = widget.checkState()
					if state == 2:
						state = True
					else:
						state = False
					settings[category][widget_name] = state
				elif isinstance(widget, dict):
					checked = []
					for _ in widget.keys():
						if widget[_].checkState(1) == Qt.Checked:
							checked.append(_)
					settings[category][widget_name] = checked
				else:
					print(widget.__class__)
					print("This should never happen..")
					raise NotImplementedError

		return settings

	def init_tree(self):

		header = QTreeWidgetItem(["Parameter", "Value", "Description"])

		self.treeWidget.setHeaderItem(
			header
		)  # Another alternative is setHeaderLabels(["Tree","First",...])

		self.treeWidget.header().resizeSection(0, 300)
		self.treeWidget.header().resizeSection(1, 150)

		# Main Categories

		with open(SETTINGS_TEMPLATE_PATH, "r") as config_file:
			self.settings_template = yaml.load(config_file, Loader=yaml.FullLoader)

		self.categories = {}

		for category in self.settings_template.keys():
			self.categories[category] = {}
			self.categories[category]["Tree"] = QTreeWidgetItem(
				self.treeWidget, [category]
			)

			fields = {}
			widgets = {}

			self.categories[category]["fields"] = fields
			self.categories[category]["widgets"] = widgets

			for subcategory in self.settings_template[category]:
				fields[subcategory] = QTreeWidgetItem(
					self.categories[category]["Tree"], [subcategory]
				)

				type = self.settings_template[category][subcategory]["type"]

				if type == "spinbox":
					widgets[subcategory] = QSpinBox()
					widgets[subcategory].setMinimum(
						self.settings_template[category][subcategory]["min"]
					)
					widgets[subcategory].setMaximum(
						self.settings_template[category][subcategory]["max"]
					)
					widgets[subcategory].setValue(
						self.settings_template[category][subcategory]["default"]
					)
					widgets[subcategory].setFocusPolicy(Qt.StrongFocus)

				elif type == "doublespinbox":
					widgets[subcategory] = QDoubleSpinBox()
					widgets[subcategory].setMinimum(
						self.settings_template[category][subcategory]["min"]
					)
					widgets[subcategory].setMaximum(
						self.settings_template[category][subcategory]["max"]
					)
					widgets[subcategory].setValue(
						self.settings_template[category][subcategory]["default"]
					)
					widgets[subcategory].setFocusPolicy(Qt.StrongFocus)

				elif type == "combobox":
					widgets[subcategory] = QComboBox()
					for _ in self.settings_template[category][subcategory]["value"]:
						widgets[subcategory].addItem(_)

					default_idx = widgets[subcategory].findText(
						self.settings_template[category][subcategory]["default"]
					)
					widgets[subcategory].setCurrentIndex(default_idx)
					widgets[subcategory].setFocusPolicy(Qt.StrongFocus)

				elif type == "checkbox":
					widgets[subcategory] = QCheckBox()
					default_state = self.settings_template[category][subcategory][
						"default"
					]
					widgets[subcategory].setChecked(default_state)

				elif type == "path":
					# Make path clickable
					pass

				elif type == "checkgroup":
					pass

				else:
					print(category, subcategory)
					raise NotImplementedError

				if subcategory in widgets.keys():
					self.treeWidget.setItemWidget(
						fields[subcategory], 1, widgets[subcategory]
					)
					try:
						description = self.settings_template[category][subcategory][
							"description"
						]
						self.treeWidget.setItemWidget(
							fields[subcategory], 2, QLabel(description)
						)
					except KeyError:
						pass

				if type == "checkgroup":
					elements = self.settings_template[category][subcategory]["value"]

					widgets[subcategory] = {}
					# ADD children
					for _ in elements.keys():
						widgets[subcategory][_] = QTreeWidgetItem(
							fields[subcategory], ["", _, elements[_]]
						)
						widgets[subcategory][_].setCheckState(1, Qt.Unchecked)

					default = self.settings_template[category][subcategory]["default"]

					for _ in default:
						widgets[subcategory][_].setCheckState(1, Qt.Checked)

					description = self.settings_template[category][subcategory][
						"description"
					]
					self.treeWidget.setItemWidget(
						fields[subcategory], 2, QLabel(description)
					)

	def disable_settings(self):
		"""
		Disable editing of settings
		"""
		for category in self.categories.keys():
			for widget_name in self.categories[category]["widgets"].keys():
				widget = self.categories[category]["widgets"][widget_name]
				if isinstance(widget, QSpinBox):
					widget.setEnabled(False)
				elif isinstance(widget, QDoubleSpinBox):
					widget.setEnabled(False)
				elif isinstance(widget, QPushButton):
					widget.setEnabled(False)
				elif isinstance(widget, QComboBox):
					widget.setEnabled(False)
				elif isinstance(widget, QCheckBox):
					widget.setEnabled(False)
				elif isinstance(widget, dict):
					for _ in widget.keys():
						widget[_].setFlags(Qt.NoItemFlags)
				else:
					print(widget.__class__)
					print("This should never happen..")
					raise NotImplementedError
	#def enable_settings(self):

	def set_settings(self, settings):
		for category in settings.keys():
			if category != 'experiment':
				for subcategory in settings[category].keys():
					if (subcategory != 'fasta_files') and (subcategory != 'database_path'):
						value = settings[category][subcategory]
						widget = self.categories[category]["widgets"][subcategory]
						if isinstance(widget, QSpinBox):
							widget.setValue(value)
						elif isinstance(widget, QDoubleSpinBox):
							widget.setValue(value)
						elif isinstance(widget, QPushButton):
							widget.setText(value)
						elif isinstance(widget, QComboBox):
							# Find and set
							idx = widget.findText(value)
							widget.setCurrentIndex(idx)
						elif isinstance(widget, QCheckBox):
							if value:
								widget.setCheckState(2)
							else:
								widget.setState(False)
						elif isinstance(widget, dict):
							checked = []
							for _ in widget.keys():
								widget[_].setCheckState(1, Qt.Unchecked)
							if value:
								for _ in value:
									widget[_].setCheckState(1, Qt.Checked)

						else:
							print("Error")
							raise NotImplementedError
