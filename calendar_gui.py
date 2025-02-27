
import sys
import sqlite3
import os
import gradio as gr

from PIL import Image
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QFileDialog, QVBoxLayout, QWidget, QMessageBox, QCalendarWidget
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtCore import Qt, QDate
from transformers import AutoProcessor, VisionEncoderDecoderModel, pipeline


from gradio_client import Client, handle_file

#connecting to  Hugging Face Space

from gradio_client import Client, handle_file

client = Client("https://zoe911-ocr-c.hf.space/")
result = client.predict(
		image=handle_file('https://raw.githubusercontent.com/gradio-app/gradio/main/test/test_files/bus.png'),
		api_name="/predict"
)
print(result)

#processor = AutoProcessor.from_pretrained("kneelesh48/Tesseract-OCR")
#model = AutoModelForImageTextToText.from_pretrained("kneelesh48/Tesseract-OCR")


# Set the path for Tesseract OCR 
#pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"



# Create the SQLite database for storing events
conn = sqlite3.connect('identifier.sqlite')
cursor = conn.cursor()

# Create the events table if it does not exist
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

# Functions
class CalendarApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        #load Hugging face model

        self.client = None
        self.load_api_client()
    def load_api_client(self):
        try:
            self.client = Client("Zoe911/OCR-C")
            print("API client loaded successfully.")
        except Exception as e:
            print(f"Failed to load API client: {str(e)}")
            self.client = None


    def predict_with_client(self, image_path):
         try:
                # 文件路径转为文件对象（如果外部服务需要文件对象）
            processed_image = self.process_image(image_path)
            result = self.client.predict(
                image=processed_image,  # 传入图片文件
                api_name="/predict"  # 您的 API 名称
            )
            return result
         except Exception as e:
             print(f"Prediction failed: {str(e)}")  # 打印日志
             return None


    def initUI(self):
        # initiate UI


        # Set the window title and geometry

        self.setWindowTitle("OCR Calendar")
        self.setGeometry(100, 100, 800, 600)
        self.setAcceptDrops(True)
# UI elements
        self.label = QLabel("Drag and Drop Screenshot Here")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("border: 2px dashed #aaa; font-size:18px; padding: 10px;")
        self.calendar = QCalendarWidget(self) # Add a calendar widget
        self.calendar.setGridVisible(True) # grid lines visible
        self.upload_button = QPushButton("select screenshot")
        self.upload_button.clicked.connect(self.open_file_dialog)# Add a button to open the file dialog

        # arrange widgets in a vertical layout
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.calendar)
        layout.addWidget(self.upload_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container) #set the main widget
#file drag event
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept() # Accept the drag event
        else:
            event.ignore()
#file drop event
    def dropEvent(self, event):
        event.accept()
        file_url = event.mimeData().urls()[0]
        image_path = file_url.toLocalFile()

        if not os.path.exists(image_path):
            QMessageBox.critical(self, "Error", "The file does not exist.")
            return
        #see if vaild image
        valid_image_extensions = [".png", ".jpg", ".jpeg",".bmp",".gif"]
        if not any(image_path.lower().endswith(ext) for ext in valid_image_extensions):
            QMessageBox.critical(self, "Error", "Invalid image file.")
            return

        # image process logic
        extracted_text = self.process_image(image_path)
        if extracted_text:
            QMessageBox.information(self, "Success","Image processed successfully.")
            #adding to calendar
            appointment_info = self.parse_appointment(extracted_text)
            if appointment_info:
                self.add_event_to_calendar(appointment_info)
            else:
                QMessageBox.critical(self, "Error", "Failed to parse appointment information.")
        else:
            QMessageBox.warning(self, "Warning", "No text extracted from the image.")
            #except Exception as e:
             #   QMessageBox.critical(self,"Error",f"An unexpected error occurred: {str(e)}")



    def handle_file(self,file_path):



         if not os.path.exists(file_path):
             raise ValueError(f"File does not exist: {file_path}")

         # 检查文件是否是图片（验证格式）
         try:
             with Image.open(file_path) as img:
                 img.verify()
         except Exception as e:
             raise ValueError(f"Invalid image file: {file_path}")
         return file_path

         # Open file dialog to select an image manually
    def open_file_dialog(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Screenshot", "", "Images (*.png *.jpg *.jpeg)", options=options)

        if file_path:

            extracted_text= self.process_image(file_path) # Process the selected image
            if extracted_text:
                QMessageBox.information(self, "Extracted Text", extracted_text)

    # Process the image: Extract text, parse appointment, and update calendar
    def process_image(self, image_path):

        if not self.processor or not self.model:
            QMessageBox.critical(self, "Error", "Model not loaded. Please load the model first.")
            return None
        try:
            image = Image.open(image_path).convert("RGB")
            pixel_values = self.processor(image, return_tensors="pt").pixel_values

            output_ids = self.model.generate(pixel_values)
            #conver to text
            result_text = self.processor.batch_decode(output_ids, skip_special_tokens=True)[0]
            return result_text
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error processing image: {(e)}")
            return None

    def extract_text(self, file_path):
        """
            使用 HuggingFace 模型从图片路径中提取文本
            :param file_path: 图片路径 (str)
            :return: 提取的文本 (str)
            """
        try:
            # 加载图片并预处理
            image = Image.open(file_path).convert("RGB")
            pixel_values = self.processor(image, return_tensors="pt").pixel_values

            # 模型推理
            output_ids = self.model.generate(pixel_values)

            # 解码结果为文本
            text = self.processor.batch_decode(output_ids, skip_special_tokens=True)[0]

            return text  # 返回提取的文本

        except FileNotFoundError:
            raise Exception("File not found. Please check the file path and try again.")
        except IOError:
            raise Exception("Invalid image format. Please provide a valid image file。")
        except Exception as e:
            raise Exception(f"Failed to Extract file: {e}")

    # Use LLM (Flan-T5) to parse the extracted text and extract structured appointment info
    def parse_appointment(self, text):
        from transformers import pipeline
        nlp = pipeline("text2text-generation", model="google/flan-t5-base")
        response = nlp(f"Extract the appointment details from the following text: {text}. Return in JSON format including title, start_time, end_time, location, and description.")[0]['generated_text']
        print("AI Output:", response)  # Print AI-generated appointment details
        return {
            "title": "Sample Appointment",
            "start_time": "2025-02-15T10:00:00",
            "end_time": "2025-02-15T11:00:00",
            "location": "Shanghai",
            "description": "Doctor visit"
        }

    # Add parsed appointment data to the SQLite database and update the calendar UI
    def add_event_to_calendar(self, appointment_info):
        cursor.execute('''
            INSERT INTO events (title, start_time, end_time, location, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (appointment_info["title"], appointment_info["start_time"], appointment_info["end_time"], appointment_info["location"], appointment_info["description"]))
        conn.commit()  # Save to database

        # Update the calendar UI (highlight the selected date)
        event_date = QDate.fromString(appointment_info["start_time"].split("T")[0], "yyyy-MM-dd")
        self.calendar.setSelectedDate(event_date)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CalendarApp()
    window.show()
    sys.exit(app.exec())  # Start the PyQt application
