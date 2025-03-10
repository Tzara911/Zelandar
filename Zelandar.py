import sys
import sqlite3
import os
import platform
import re
from datetime import datetime, timedelta
from dateutil.rrule import rrule, WEEKLY, MO, TU, WE
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QPushButton, QFileDialog,
                             QVBoxLayout, QWidget,QListWidget,QListWidgetItem, QMessageBox, QCalendarWidget,
                             QLineEdit, QTextBrowser, QHBoxLayout, QDialog, QStyle)
# Updated import
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPainter, QBrush, QColor
from PyQt6.QtCore import Qt, QDate, QPropertyAnimation, QRect, QSize

from gradio_client import Client, handle_file
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPainter, QBrush, QColor
from PyQt6.QtWidgets import QStyle


# Process finished with exit code 1ite database initialization
conn = sqlite3.connect('identifier.sqlite')
cursor = conn.cursor()

# Create events table without duration column
cursor.execute('''
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,  
        title TEXT,  
        start_time TEXT,  
        end_time TEXT,  
        location TEXT,  
        description TEXT
    )
''')
conn.commit()


# Screenshot folder monitoring handler
class ScreenshotHandler(FileSystemEventHandler):
    def __init__(self, app):
        self.app = app

    def on_created(self, event):
        if not event.is_directory:
            file_path = event.src_path
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                print(f"New screenshot detected: {file_path}")
                self.app.process_image(file_path)


def get_default_screenshot_path():
    # Determine default screenshot path based on OS
    system = platform.system()
    if system == "Windows":
        return os.path.join(os.environ["USERPROFILE"], "Pictures", "Screenshots")
    elif system == "Darwin":  # macOS
        return os.path.expanduser("~/Desktop")
    elif system == "Linux":
        return os.path.expanduser("~/Pictures")
    else:
        return os.path.expanduser("~/Desktop")


def start_screenshot_monitor(app):
    # Start monitoring the screenshot folder
    screenshot_dir = get_default_screenshot_path()
    if not os.path.exists(screenshot_dir):
        print(f"Default screenshot folder does not exist: {screenshot_dir}")
        return
    event_handler = ScreenshotHandler(app)
    observer = Observer()
    observer.schedule(event_handler, screenshot_dir, recursive=False)
    observer.start()
    print(f"Monitoring screenshot folder: {screenshot_dir}")


class EventDialog(QDialog):
    def __init__(self, events, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Event Details")
        self.setMinimumSize(400, 300)

        layout = QVBoxLayout()
        for event in events:
            title, start_time, end_time, location, description = event
            if start_time and end_time:
                for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"]:
                    try:
                        start_dt = datetime.strptime(start_time, fmt)
                        end_dt = datetime.strptime(end_time, fmt)
                        duration_hours = (end_dt - start_dt).total_seconds() / 3600
                        duration_text = f"{duration_hours:.1f} hours"
                        break
                    except ValueError:
                        duration_text = "Unknown"
            else:
                duration_text = "Unknown"
            event_text = f"Title: {title}\nStart: {start_time}\nEnd: {end_time}\nLocation: {location}\nDuration: {duration_text}\nDescription: {description or 'No description'}\n"
            layout.addWidget(QLabel(event_text))
        self.setLayout(layout)


class CustomCalendarWidget(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.events_by_date = {}  # Store events by date
        self.clicked.connect(self.show_event_details)

    def paintCell(self, painter: QPainter, rect: QRect, date: QDate):
        # Default painting
        super().paintCell(painter, rect, date)
        date_str = date.toString("yyyy-MM-dd")
        # Highlight dates with events
        if date_str in self.events_by_date:
            events = self.events_by_date[date_str]
            painter.save()
            painter.setBrush(QBrush(QColor(255, 215, 0, 100)))  # Light gold for events
            painter.drawRect(rect.adjusted(1, 1, -1, -1))
            painter.restore()
            painter.setPen(QColor(0,0,0))  # 
            font = painter.font()
            dynamic_font_size = max(6, rect.height() // (len(events) + 2))  # fit the grid
            font_size = dynamic_font_size
            font.setPointSize(font_size)
            painter.setFont(font)

            # status bar display
            y_offset = rect.top() + dynamic_font_size  
            max_events = max(len(events), 2)  
            line_spacing = max(12, dynamic_font_size + 2)  
            for i in range(max_events):
                event = events[i]
                title = event.get("title", "Event")
                start_time = event.get("start_time", "").split(" ")[1] if event.get("start_time") else "?"
                location = event.get("location", "Unknown")

                event_text = f"{start_time} {title} ({location})"  # show time and title
                #display in grid
                painter.drawText(rect.left() + 2, y_offset, rect.width()-4, rect.height(),
                 Qt.AlignmentFlag.AlignLeft, event_text)

                y_offset += font.pointSize()+2
    def update_events(self, events):
        
        # Update events_by_date with new events, handling multiple time formats
        self.events_by_date.clear()
        for event in events:
            if event["start_time"]:
                # Try multiple formats for parsing
                for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"]:
                    try:
                        date_obj = datetime.strptime(event["start_time"], fmt)
                        date_str = date_obj.strftime("%Y-%m-%d")
                        if date_str not in self.events_by_date:
                            self.events_by_date[date_str] = []
                        self.events_by_date[date_str].append(event)
                        break
                    except ValueError:
                        continue
                else:
                    print(f"Could not parse start_time: {event['start_time']}")
            self.update()
    def show_event_details(self, date):
        # Show dialog with events for the selected date
        date_str = date.toString("yyyy-MM-dd")
        if date_str in self.events_by_date:
            events = self.events_by_date[date_str]
            dialog = EventDialog(events, self)
            dialog.exec()


class ChatWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(100)
        self.setStyleSheet("background-color: #f0f0f0; border-top: 1px solid #ccc;")

        layout = QVBoxLayout(self)
        #status display
        self.chat_display = QTextBrowser(self)
        self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display)
        #input box and send botton
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText("Enter message or voice command...")
        self.input_field.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_field)

        self.send_button = QPushButton("Send", self)
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_button)

        layout.addLayout(input_layout)
        self.setLayout(layout)

    def send_message(self):
        #send the message from the input
        message = self.input_field.text().strip()
        if message:
            self.chat_display.append(f"You: {message}")
            self.input_field.clear()
            self.chat_display.append("Message received! (Feature to be expanded)")


class CalendarApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.client = None
        self.load_api_client()
        self.chat_visible = False
        start_screenshot_monitor(self)

    def load_api_client(self):
        # Load OCR API client
        try:
            self.client = Client("Zoe911/OCR-C")
            print("API client loaded successfully.")
        except Exception as e:
            print(f"Failed to load API client: {str(e)}")
            self.client = None

    def init_ui(self):
        # Initialize UI components
        self.setWindowTitle("OCR Calendar with Chat")
        self.setGeometry(100, 100, 900, 700)
        self.setAcceptDrops(True)

        main_layout = QVBoxLayout()
        self.calendar = CustomCalendarWidget(self)  # Use custom calendar
        self.calendar.setGridVisible(True)
        self.calendar.setStyleSheet("QCalendarWidget { font-size: 14px; }")
        main_layout.addWidget(self.calendar,5)
#select file botton
        self.upload_button = QPushButton("Select Screenshot", self)
        self.upload_button.clicked.connect(self.open_file_dialog)
        main_layout.addWidget(self.upload_button)
#drop area
        self.drop_label = QLabel("Drag and drop screenshot here", self)
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setStyleSheet("border: 2px dashed #aaa; font-size: 18px; padding: 10px;")
        main_layout.addWidget(self.drop_label)
#list of event
        self.event_list = QListWidget(self)
        self.event_list.setStyleSheet("font-size: 14px; padding: 5px;")
        main_layout.addWidget(self.event_list,1)
        self.refresh_event_list()

        self.chat_widget = ChatWidget(self)
        main_layout.addWidget(self.chat_widget,1)
# main winds layout
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.chat_animation = QPropertyAnimation(self.chat_widget, b"geometry")
        self.chat_animation.setDuration(300)

    def refresh_event_list(self):
        # Refresh event list from database and calculate duration dynamically
        self.event_list.clear()
        cursor.execute("SELECT title, start_time, end_time, location, description FROM events")
        events = cursor.fetchall()
        calendar_events = []
        for event in events:
            title, start_time, end_time, location, description = event
            if start_time and end_time:
                # Try multiple formats for parsing
                for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"]:
                    try:
                        start_dt = datetime.strptime(start_time, fmt)
                        end_dt = datetime.strptime(end_time, fmt)
                        duration_hours = (end_dt - start_dt).total_seconds() / 3600
                        duration_text = f"{duration_hours:.1f} hours"
                        break
                    except ValueError:
                        continue
                else:
                    duration_text = "Unknown"
            else:
                duration_text = "Unknown"
            display_text = f"{title} | {start_time} - {end_time} | {location} | Duration: {duration_text}"
            item = QListWidgetItem(display_text)
            item.setToolTip(description or "No description")
            self.event_list.addItem(item)
            # Store event for calendar highlighting
            calendar_events.append(
                {"title": title, "start_time": start_time, "end_time": end_time, "location": location,
                 "description": description})

        self.calendar.update_events(calendar_events)

    def mouseMoveEvent(self, event):
        # Show/hide chat widget based on mouse position
        margin_height = 50
        calendar_bottom = self.calendar.geometry().bottom()
        chat_trigger_y = calendar_bottom + margin_height
        if event.pos().y() > chat_trigger_y and not self.chat_visible:
            self.show_chat()
        elif event.pos().y() <= chat_trigger_y and self.chat_visible:
            self.hide_chat()

    def show_chat(self):
        # Animate chat widget to appear
        if not self.chat_visible:
            start_geometry = QRect(0, self.height(), self.width(), 0)
            end_geometry = QRect(0, self.height() - 200, self.width(), 200)
            self.chat_animation.setStartValue(start_geometry)
            self.chat_animation.setEndValue(end_geometry)
            self.chat_animation.start()
            self.chat_visible = True

    def hide_chat(self):
        # Animate chat widget to hide
        if self.chat_visible:
            start_geometry = QRect(0, self.height() - 200, self.width(), 200)
            end_geometry = QRect(0, self.height(), self.width(), 0)
            self.chat_animation.setStartValue(start_geometry)
            self.chat_animation.setEndValue(end_geometry)
            self.chat_animation.start()
            self.chat_visible = False

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        file_url = event.mimeData().urls()[0]
        image_path = file_url.toLocalFile()
        self.process_image(image_path)

    def open_file_dialog(self):
        # Open file dialog to select screenshot
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Screenshot", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.process_image(file_path)

    def process_image(self, image_path):
        # Process screenshot and add events to calendar
        if not os.path.exists(image_path):
            QMessageBox.critical(self, "Error", "File does not exist")
            return
        result = self.predict_with_client(image_path)
        if result:
            print(f"OCR result: {result}")
            appointment_infos = self.parse_appointment(result)
            if appointment_infos:
                for info in appointment_infos:
                    self.add_event_to_calendar(info)
                QMessageBox.information(self, "Success", f"Added {len(appointment_infos)} events to calendar")
                self.refresh_event_list()

    def predict_with_client(self, image_path):
        # Call OCR API to extract text from image
        if not self.client:
            return None
        try:
            result = self.client.predict(image=handle_file(image_path), api_name="/predict")
            return result
        except Exception as e:
            print(f"Prediction failed: {str(e)}")
            return None
    client = Client("Zoe911/spaCy-C")
    def parse_appointment(self, text):
      #Process OCR-extracted text and use the spaCy-C model to extract structured event information.
        appointment_infos = []
        lines = text.split('\n')
        recurring_events = {}
        location = None  # Default location if not specified
        event_name = "Untitled Event" #default
        duration = "Unknow" #default
        start_time = None
        end_time = None
       
       #send OCR text to spaCy-C API
        try:   
            ner_response = self.client.predict(
                text = text,
                api_name="/predict"
            )
        except Exception as e:
            print(f"Error calling spaCy-C API: {e}")
            return []    
        # Parse API response (assuming the response is a list of dictionaries)
        entities = {ent["entity"]: ent["word"] for ent in ner_response}
          
        # extract recognized entities
        event_name = entities.get("EVENT", event_name)
        location = entities.get("GPE", location)
        start_time = entities.get("TIME", None)
        end_time = None  
        # convert start time to 24hour format 
        if start_time:
            try:
                start_time_obj = datetime.strptime(start_time, "%I:%M %p") if "AM" in start_time or "PM" in start_time else datetime.strptime(start_time, "%H:%M")
                start_time = start_time_obj.strftime("%H:%M")
            except Exception as e:
                print(f"Error parsing star time: {e}")
                start_time = "Unknown"

          # Generate status bar message
        status_bar_text = f"{event_name} | {location} | Duration: {duration}"
        print(f"DEBUG - status_bar_text: {status_bar_text}")
        
             
             # Create structured event output
        appointment_info = {
            "title": event_name,
            "start_time": start_time or "Unknown",
            "end_time": end_time or "Unknown",
            "duration": duration,
            "location": location,
            "description": text
            }

        appointment_infos.append(appointment_info)

        return appointment_infos
            


    def add_event_to_calendar(self, appointment_info):
        # Add event to database and update calendar
        cursor.execute('''
            INSERT INTO events (title, start_time, end_time, location, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (appointment_info["title"], appointment_info["start_time"],
              appointment_info["end_time"], appointment_info["location"],
              appointment_info["description"]))
        conn.commit()
        if appointment_info["start_time"]:
            event_date = QDate.fromString(appointment_info["start_time"].split(" ")[0], "yyyy-MM-dd")
            self.calendar.setSelectedDate(event_date)
            # Update calendar to highlight this date
            self.refresh_event_list()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CalendarApp()
    window.show()
    try:
        sys.exit(app.exec())
    except SystemExit:
        conn.close()