from watchdog.events import FileSystemEventHandler
from PyQt6.QtGui import QPainter, QBrush, QColor, QDragEnterEvent, QDropEvent, QPixmap
from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow, QApplication, QCalendarWidget, QDialogButtonBox, QTextEdit, QLabel, QVBoxLayout, QWidget, QToolTip, QMessageBox, QPushButton
from PyQt6.QtCore import QBuffer, QDate, QIODevice, Qt
import requests
import json
from collections import deque
import re
import sqlite3
from datetime import datetime
import sys
import traceback  # Import traceback module
# Updated import
from PIL import Image
from gradio_client import Client, handle_file  # Import Client and handle_file from gradio_client
import base64
import io

import numpy as np

# Database initialization
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

class MyCalendar(QCalendarWidget):
    def __init__(self,parent = None):
        super().__init__(parent)
        # store events by date
        self.events = {}
    #Override the default paintCell behavior of QCalendarWidget，
    # Qt's built-in calendar widget is display-only and does not natively support event marking or cell customization. This overridden method enables custom prainting logic
    # visually highlight dates that have events   
    #render the default calendar cell first
    def paintCell(self, painter: QPainter, rect, date: QDate):
        super().paintCell(painter,rect,date)
     # if the date has events, highlight it   
        if date in self.events:
            painter.save()
            painter.fillRect(rect, QColor(255,192,203,180))# fill with  Light pink with transparency
            painter.setPen(Qt.GlobalColor.white)
            #   Draw a small 📌 icon at the bottom-center of the cell
            painter.drawText(rect,Qt.AlignmentFlag.AlignBottom| Qt.AlignmentFlag.AlignHCenter,"📌")  
            painter.restore()
        
class CalendarApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.events = {}
        # Initialize Hugging Face clients
        self.load_api_client() 

        # loading UI file
        uic.loadUi(r"C:\Users\Tzara911\OneDrive\Documents\GitHub\Zelandar\mainwindow.ui", self)
       # self.calendarWidget.selectionChanged.connect(self.on_date_selected)
        # find the pushbotton from the UI and connect it to the click handler
        self.ok_button = self.findChild(QPushButton, "ok_button")
        if self.ok_button:
            print(" OK button found")
            self.ok_button.clicked.connect(self.on_ok_clicked)# hook
        else:
            print(" OK button not found")
            
        # replace textEdit to MyTextEdit 
        self.textEdit = MyTextEdit(self)
        self.textEdit.setGeometry(self.findChild(QTextEdit, "textEdit").geometry())  #
        self.textEdit.setObjectName("textEdit")  
        self.layout().replaceWidget(self.findChild(QTextEdit, "textEdit"), self.textEdit)  
 
        # replace calendar to MyCalendar
        self.calendar = self.findChild(QCalendarWidget, "calendarWidget")
        self.calendar = MyCalendar(self)
        calendar_ui = self.findChild(QCalendarWidget, "calendarWidget")
        if calendar_ui:
            self.calendar.setGeometry(calendar_ui.geometry())
        else:
            print("Error: Calendar widget not found in UI!")
        if not self.calendar:
            print("Error: Calendar widget not found in UI!")
        self.layout().replaceWidget(calendar_ui, self.calendar) 
        calendar_ui.setParent(None) # delete the original 
        self.setWindowTitle("Zelandar")
        
        # Find the static Qlabel from the ui file and replace it with a MyQlabel, which supports drag and drop function later
        ui_label = self.findChild(QLabel, "label")
        if ui_label:
            # create a new custom label(MyDropLabel)
            self.dropLabel = MyDropLabel(self)
            self.dropLabel.setGeometry(ui_label.geometry())
            self.dropLabel.setObjectName("dropLabel")
            # replace the original QLabel with dropLabel in layout
            self.layout().replaceWidget(ui_label, self.dropLabel)
            ui_label.setParent(None) # delete old one 
            # style the new drop area
            self.dropLabel.setText("Drag Image Here")
            self.dropLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.dropLabel.setStyleSheet("border: 2px dashed #aaa; font-size: 14px; color: gray;")
        else:
            print("Cannot find dropLabel")    
  # placeholder for ocr result in textbox
        if hasattr(self, "textEdit"):
            self.textEdit.setPlaceholderText("OCR result will appear here...")
        else:
            print("Warning: `textEdit` not found in UI!")
        #initialize calendar events dictionary and refresh UI
        self.calendar.events = {}    
        self.calendar.updateCells() 

        # Bind OK button's click event
        if hasattr(self, "buttonBox"):
            self.ok_button = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
            if self.ok_button:
                self.ok_button.clicked.connect(self.on_ok_clicked)
        # store all the parsed events, grouped by date
        self.events_by_date = {}
        #Tracks the most recent 4 event  for displaying in scroll areas
        self.recent_texts = deque(maxlen=4)
        
    #def on_date_selected(self):
    
     # Clear any existing content
     
    # Get the selected date from the calendar widget in "YYYY-MM-DD" 
    # Connect to database
       
    
    # Query the database for all events that match the selected date
       
    
    # First, clear all scroll areas， If there are events found for the selected date
       
    # Display each event in a separate scroll area
           
            
    # Extract just the time part from start_time and end_time
   
    # Update the sscroll area with this event
               
    # Add event text to this  scroll area
                  
           
     # If no events found for this date, display a message in the first scroll area
             
    # Add "No events" message
              
     # this function is use to refresh the cdrollabel sections in the UI that show parsed events from NER result                    
    def update_scroll_area(self, new_text,  replace=True):
      
        self.recent_texts.append(new_text)# append new text to the recent_texts queue
        print(f"Queue length after append: {len(self.recent_texts)}")
    
    
        scroll_area_names = ["scrollArea_1", "scrollArea_2", "scrollArea_3", "scrollArea_4"]
    
    # get the moset recent 4 items to display
        recent_items = list(self.recent_texts)[-4:]  
    
    # loop through each scroll area and populate it with new content
        for i, text in enumerate(recent_items):
            if i >= len(scroll_area_names):
                print(f"No available scroll area for index {i}, skipping...")
                continue
        
            scroll_area_name = scroll_area_names[i]
            scroll_area = getattr(self, scroll_area_name, None)
        
            if not scroll_area:
                print(f"{scroll_area_name} not found in UI!")
                continue
        
        # get existing content widget inside the scroll area
            content_widget = scroll_area.widget()
        
        #  if no cntent widget exists, creata a new layout, 
            if not content_widget:
                content_widget = QWidget()
                scroll_area.setWidget(content_widget)
                scroll_area.setWidgetResizable(True)
            
            
                layout = QVBoxLayout(content_widget)
                content_widget.setLayout(layout)
            else:
            
                layout = content_widget.layout()
            
            # create layout if not already yet
                if not layout:
                    layout = QVBoxLayout(content_widget)
                    content_widget.setLayout(layout)
                
            # clear existing widgets in the layout to prevent duplication
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()
        
        # ensure the text is in list format
            if isinstance(text, list):
                formatted_text = text
            else:
                formatted_text = text.split("\n") if "\n" in text else [text]
        
        # add each lie of txt as a new QLabel in the scroll area
            for line in formatted_text:
                if line:  # skip empty lines
                    new_label = QLabel()
                    new_label.setTextFormat(Qt.TextFormat.PlainText)
                    new_label.setWordWrap(True)
                    new_label.setText(str(line))  # ensure it is a string
                    layout.addWidget(new_label)
        
            print(f"Updated {scroll_area_name} with content")
                 
    def process_text(self, input_text=None):
        print("🧪 self.spacy_client =", getattr(self, "spacy_client", " NOT SET"))
        if input_text is None:
            input_text = self.textEdit.toPlainText().strip()
        
        if not input_text:
            # show a warning if the input field is empty
            QMessageBox.warning(self, "Warning", "Please enter some text to process.")
            return
        try:
            if self.spacy_client:
                # send the input text to the deployed spaCy-like NER model API
                print(f"Sending text to spaCy API: {input_text}")
                ner_result = self.spacy_client.predict(text=input_text, api_name="/predict")
                # raw response from model
                print(f"spaCy API Response: {ner_result}")
                # Format the returned dict into a readable content(string)
                if isinstance(ner_result, dict):
                    formatted_text = "\n".join([f"{key}: {value}" for key, value in ner_result.items()])
                else:
                    formatted_text = str(ner_result)# fallback if not dict (edge case)
                # Display the result in the text editor     
                self.textEdit.setText(formatted_text)
                print(f"Parsed Text: {formatted_text}")
                #self.update_scroll_area(formatted_text)
                
                # convert NER result into one or more structured appointment
                appointment_infos = self.parse_appointment(ner_result)
                # add appointment to the calendar and database
                for appointment_info in appointment_infos:
                    # convert string date to QDate
                    date_str = appointment_info.get("date")
                    
                    if date_str:  # ensure date_str is valid
                        qdate = QDate.fromString(date_str, "yyyy-MM-dd")
                        
                        if qdate.isValid():
                            if qdate not in self.calendar.events:
                                self.calendar.events[qdate] = []
                            self.calendar.events[qdate].append(appointment_info)
                        else:
                            print(f"Invalid date: {date_str}")
                    else:
                        print("No date found in appointment_info")  # log for the invaild date 
                        
                self.calendar.updateCells() 
                        
                # Debug print: check current calendar data structure
                print("📅 Current calendar events:")
                for date, events in self.calendar.events.items():
                    print(f"{date.toString('yyyy-MM-dd')}:")
                    for event in events:
                        print(f"   - {event}")    
                return formatted_text           
           
            else:
                QMessageBox.critical(self, "Error", "spaCy API client not available. Please check the connection.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to process text with spaCy API: {str(e)}")
            print(f"Error processing text: {str(e)}")
            return
    
        # replace default QTextEdit with MyTextEdit
        self.text_input = MyTextEdit(self)
        self.layout().replaceWidget(self.textEdit, self.text_input)
        self.textEdit = self.text_input
        
    def load_api_client(self):
        # load API clients from Hugging Face Space
        try:
            # Initialize spaCy NER client
            self.spacy_client = Client("Zoe911/spaCy-C")
            print("spaCy API client loaded successfully.")
            
            # Initialize OCR client
            self.ocr_client = Client("Zoe911/OCR-C")
            print("OCR API client loaded successfully.")
        except Exception as e:
            print(f"Failed to load API clients: {str(e)}")
            self.spacy_client = None
            self.ocr_client = None
             
    def process_image(self, image_path=None):
        print(" Entered process_image with path:", image_path)
        
        try:
            if image_path:
                print("Sending image to OCR API...")
                
                # Send image to the Hugging Face OCR model
                # required because the Gradio API expects a file-like input, not just a file 
                ocr_result = self.ocr_client.predict(
                    handle_file(image_path),
                    api_name="/predict"
                )
                
                print(f"OCR Result: {ocr_result}")
                
                if not ocr_result:
                    print("OCR failed, no result returned.")
                    return "OCR failed, no result found."
                
                # Update textEdit with OCR result
                self.textEdit.setPlainText(ocr_result)
                
                # Process the extracted text with NER
                self.process_text(input_text=ocr_result)
                
                return ocr_result
            else:
                print("No image path provided.")
                return "No image provided."
                
        except Exception as e:
            error_message = f"Error in process_image: {str(e)}"
            print(error_message)
            traceback.print_exc()  # Print full error stack
            return error_message
         
    def on_ok_clicked(self):
        # Handle push click: send text or img input for processing 
        print("on_ok_clicked!")

        # First check for text input
        if hasattr(self, "textEdit"):
            print("Have text")
            text = self.textEdit.toPlainText().strip()
            if text:
                print("Found text, processing...")
                formatted_text = self.process_text(input_text=text)
                print("Updating scroll area")
                self.update_scroll_area(formatted_text)
                print("Scroll area updated!")
                self.textEdit.clear() 
                return formatted_text
            
        # If no text, check for image
        if hasattr(self, "dropLabel") and hasattr(self.dropLabel, "image_path"):
            print("Image found! Ready for extraction")
            image_path = self.dropLabel.image_path
            
            if image_path:
                print(" Found image in dropLabel, processing image...")
                ocr_result = self.process_image(image_path=image_path)
                if ocr_result:
                    self.update_scroll_area(formatted_text)
                return

        # If neither text nor image, show warning
        QMessageBox.warning(self, "Warning", "Please drag an image or enter text.")
        
  # parse the structured NER result text into a standardized appointment dict
  
    def parse_appointment(self, ner_result):
        appointment_infos = []
        try:
            # ensures the output remains in a consistent, structured format, even if the nNER result is already standardized 
            if isinstance(ner_result, str):
                event_name = "Untitled Event"
                location = "Unknown"
                date_str = datetime.now().strftime("%Y-%m-%d")
                start_time = None
                end_time = None
                duration = "Unknown"
                description = str(ner_result)
                
                if isinstance(ner_result, str):
                    lines = ner_result.split("\n")
                    for line in lines:
                        if "Event:" in line:
                            event_name = line.split("Event:")[1].strip()
                        elif "Location:" in line:
                            location = line.split("Location:")[1].strip()
                        elif "Date:" in line:
                            date_str = line.split("Date:")[1].strip()
                        elif "Start Time:" in line:
                            start_time = line.split("Start Time:")[1].strip()
                        elif "End Time:" in line:
                            end_time = line.split("End Time:")[1].strip()
                        elif "Duration:" in line:
                            duration = line.split("Duration:")[1].strip()        
                                                        
                # Standardizing start_time and end_time
                if start_time:
                    try:
                        start_time_obj = datetime.strptime(start_time, "%H:%M")
                        start_time = start_time_obj.strftime("%H:%M")
                    except ValueError as e:
                        print(f"Error parsing start time: {e}")
                        start_time = "Unknown"
                if end_time:
                    try:
                        end_time_obj = datetime.strptime(end_time, "%H:%M")
                        end_time = end_time_obj.strftime("%H:%M")
                    except ValueError as e:
                        print(f"Error parsing end time: {e}")
                        end_time = "Unknown"

                # Assemble time
                start_time = f"{date_str} {start_time}" if start_time and start_time != "Unknown" else f"{date_str} 12:00"
                end_time = f"{date_str} {end_time}" if end_time and end_time != "Unknown" else f"{date_str} 13:00"

                appointment_info = {
                    "title": event_name,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": duration,
                    "location": location,
                    "description": str(ner_result),
                    "date": date_str
                }
                appointment_infos.append(appointment_info)
            else:
                print(f"Unexpected NER result format: {ner_result}")
        except Exception as e:
            print(f"Error parsing appointment: {e}")
        return appointment_infos
    
  
    
    def add_event_to_calendar(self, appointment_info):
        # Add event to database and update calendar
        # Insert the appointment into the SQLite database
        cursor.execute('''
            INSERT INTO events (title, start_time, end_time, location, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (appointment_info["title"], appointment_info["start_time"],
              appointment_info["end_time"], appointment_info["location"],
              appointment_info["description"]))
        conn.commit()
        cursor.execute("SELECT * FROM events")# debugging
        rows = cursor.fetchall()
        for row in rows:
            print(row)
        # Extract the date part from date
        event_date_str = appointment_info["date"]
        event_date = QDate.fromString(event_date_str, "yyyy-MM-dd")
        # Update the calendar's in_memory event dictionary
        if event_date.isValid():
            if event_date not in self.calendar.events:
                self.calendar.events[event_date] = []
            self.calendar.events[event_date].append({
                "title": appointment_info["title"],
                "time": appointment_info["start_time"].split(" ")[1],
                "location": appointment_info["location"],
                "description": appointment_info["description"]
            })
            # Update the calendar cell ui
            self.calendar.updateCells()    
            # Set the selected date to the new event's date 
            self.calendar.setSelectedDate(event_date)
            # Update calendar to highlight this date
            self.refresh_event_list()
            # Debugging: print out database
            cursor.execute("SELECT * FROM events")
            rows = cursor.fetchall()
            for row in rows:
                print(row)
            
    def mouseMoveEvent(self, event):
        # Handle mouse move to track hover on calendar
        if not hasattr(self, "calendar") or self.calendar is None:
            print("Calendar widget is not initialized yet.")
            return
        # Show/hide chat widget based on mouse position
        mouse_pos = event.pos()
        calendar_pos = self.calendar.mapFromParent(mouse_pos)
        # Convert mouse position to date
        hovered_date = self.calendar.selectedDate()  # May need a workaround
        
        if hovered_date.isValid():
            date_str = hovered_date.toString("yyyy-MM-dd")
            # Check if the date has any events
            if date_str in self.events_by_date:
                events = self.events_by_date[date_str]
                # Travel through events(event_list), create a list, use \n connect each line
                event_text = "\n".join([f"{event['title']}({event['start_time']}-{event['end_time']})" for event in events])
                # Show a tooltip near the cursor with the event details
                QToolTip.showText(event.globalPos(), event_text, self.calendar)
            else:
                QToolTip.hideText()  # Hide tooltip if no events on this date  
  
    # convert an event divtionary into a formatted string for ui display
    def format_event_text(self, event):
       
        title = event.get("title", "Untitled Event")
        start_time = event.get("start_time", "Unknown")
        end_time = event.get("end_time", "Unknown")
        location = event.get("location", "None") 
        description = event.get("description", "None")
        
        return f"{title}({start_time}-{end_time})\nLocation: {location}\n{description}" 
    
    # triggerd when a date is clicked on the calendar
    # fetches events for the selected date and displays them in the scroll area.
    def show_event_details(self, date):
        
        date_str = date.toString("yyyy-MM-dd")  # Convert date to string format
        
        if date_str in self.events_by_date:
            events = self.events_by_date[date_str]  # Get all events for this date
            event_texts = [self.format_event_text(event) for event in events]
            self.update_scroll_area(event_texts)
        else:
            self.update_scroll_area(["No events for this date."])    
    # Refresh event list from database and calculate duration dynamically  
    #and update the scroll area and calendar with structured event data.                
    def refresh_event_list(self):
        
        cursor.execute("SELECT title, start_time, end_time, location, description FROM events")
        events = cursor.fetchall()
    
        latest_results = []  # Store the latest results for scroll area
        for event in events:
            event_dict = {
                "title": event[0],
                "start_time": event[1],
                "end_time": event[2],
                "location": event[3], 
                "description": event[4]
            }
            # Calculate the duration
            duration_text = "Unknown"
            if event_dict["start_time"] and event_dict["end_time"]:
                # Try multiple formats for parsing
                for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"]:
                    try:
                        start_dt = datetime.strptime(event_dict["start_time"], fmt)
                        end_dt = datetime.strptime(event_dict["end_time"], fmt)
                        duration_hours = (end_dt - start_dt).total_seconds() / 3600
                        duration_text = f"{duration_hours:.1f} hours"
                        break
                    except ValueError:
                        continue
            # Add duration to event_dict
            event_dict["duration"] = duration_text
            display_text = self.format_event_text(event_dict) 
            latest_results.append(display_text)
        
            # Store event for calendar highlighting
            date_str = event_dict["start_time"].split(" ")[0] if event_dict["start_time"] else "Unknown"
            if date_str not in self.events_by_date:
                self.events_by_date[date_str] = []           
            self.events_by_date[date_str].append(event_dict)
            # Format event display text with start/end time and calculated duration
            display_text = f"{event_dict['title']} ({event_dict['start_time']}-{event_dict['end_time']}, Duration: {duration_text})"
            latest_results.append(display_text)
            
        # Update scrollArea with latest OCR results
        self.update_scroll_area(latest_results)       
        
        # Update calendar events
        if hasattr(self.calendar, "update_events"):
            self.calendar.update_events(self.events_by_date)


class MyDropLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)  # Enable drag and drop
        self.image_path = None
        
        # handle the darg enter event for the QLabel
        
    def dragEnterEvent(self, event):
        # #check if the dragged item contain URLs , then convert it to a local file path string
         # accepts only image files and ignores all other file types
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                    event.acceptProposedAction()  
                    return
        event.ignore()  # Ignore if not a valid image
        
        
      # Triggered when the image is dropped  
      # dropEvent handles the actual file drop after dragEnterEvent has accepted it. 
    def dropEvent(self, event):
       
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                pixmap = QPixmap(file_path)
                if not pixmap.isNull():
                    # Display the image scaled inside the label
                    self.setPixmap(pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio))                 
                    self.image_path = file_path

class MyTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)  #  inherited from CalendarApp mainwindow
        self.setPlaceholderText("Enter text here...")
       

if __name__ == "__main__":
  # Start the application
    app = QApplication(sys.argv)
    window = CalendarApp()
    
    window.show()
  # Run the event loop, and close DB connection on exit
    try:
        sys.exit(app.exec())
    except SystemExit:
        conn.close()
