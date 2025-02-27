import sqlite3


conn = sqlite3.connect("local_calendar.db")
cursor = conn.cursor()

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
conn.close()
print("📅 Initialization completed.")

def add_event(title, start_time, end_time, location, description):
    conn = sqlite3.connect('local_calendar.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO events (title, start_time, end_time, location, description)
        VALUES (?, ?, ?, ?, ?)
    ''', (title, start_time, end_time, location, description))
    
    conn.commit()
    conn.close()
    print(f"✅ event'{title}' added to the calender！")

# 示例调用
add_event("Team meeting", "2025-02-03T15:00:00", "2025-02-03T16:00:00", "office", "weekly report")

def get_all_events():
    conn = sqlite3.connect('local_calendar.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM events')
    events = cursor.fetchall()
    
    conn.close()
    
    print("\n📅 current event：")
    for event in events:
        print(f"ID: {event[0]} | title: {event[1]} | start: {event[2]} | end: {event[3]} | location: {event[4]}\n")

# 调用函数
get_all_events()

def check_conflict(start_time, end_time):
    conn = sqlite3.connect('local_calendar.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM events
        WHERE (start_time < ? AND end_time > ?) OR (start_time < ? AND end_time > ?)
    ''', (end_time, end_time, start_time, start_time))
    
    conflicts = cursor.fetchall()
    conn.close()
    
    if conflicts:
        print("⛔ time confilct")
        for event in conflicts:
            print(f"⚠ {event[1]} ({event[2]} - {event[3]})")
        return True
    else:
        print("✅ avalible！")
        return False


check_conflict("2025-02-03T15:30:00", "2025-02-03T16:30:00")
def delete_event(event_id):
    conn = sqlite3.connect('local_calendar.db')
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM events WHERE id = ?', (event_id,))
    
    conn.commit()
    conn.close()
    print(f"🗑️ Event ID {event_id} Deleted！")


delete_event(1)

def main():
    while True:
        print("\n📅 Loacal Calendar")
        print("1. Add Event")
        print("2. Events Checking")
        print("3. Time Confilct checking")
        print("4. Delete Event")
        print("5. Exit")

        choice = input("Please select an operation.(1-5）：")

        if choice == "1":
            title = input("Type in the name of the event：")
            start_time = input("type in start time（YYYY-MM-DDTHH:MM:SS）：")
            end_time = input("type in end time （YYYY-MM-DDTHH:MM:SS）：")
            location = input("type in the location：")
            description = input("type in the description of the event：")

            if not check_conflict(start_time, end_time):
                add_event(title, start_time, end_time, location, description)

        elif choice == "2":
            get_all_events()

        elif choice == "3":
            start_time = input("type in start time（YYYY-MM-DDTHH:MM:SS）：")
            end_time = input("type in end time（YYYY-MM-DDTHH:MM:SS）：")
            check_conflict(start_time, end_time)

        elif choice == "4":
            event_id = input("Chose the event that need to delete ID：")
            delete_event(int(event_id))

        elif choice == "5":
            print("👋 Exit the calendar！")
            break

        else:
            print("⚠ invaild input, please try again！")

# 运行主程序
main()


from transformers import pipeline

nlp = pipeline("text2text-generation", model="google/flan-t5-base")

def parse_event_info(text):
    """Use LLM Translate the information"""
    response = nlp(f"Analyze this task: {text}")
    parsed_data = eval(response[0]['generated_text'])  # 转换为字典
    return parsed_data

import pytesseract
from PIL import Image
pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"
def extract_text_from_image(image_path):
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image)
    return text

