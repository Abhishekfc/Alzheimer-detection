import os
import gdown
import streamlit as st
import tensorflow as tf
from PIL import Image
import numpy as np
from streamlit_option_menu import option_menu
import re
import base64
from fpdf import FPDF
import mysql.connector

model_path = "model.h5"
gdrive_url = "https://drive.google.com/uc?id=15mWlhfpuU-xlKPc9sqonX2A0Y4zjt35z"  # Corrected direct download link

# ✅ Download model if it does not exist
if not os.path.exists(model_path):
    gdown.download(gdrive_url, model_path, quiet=False)

# Connect to the MySQL database
try:
    mydb = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Abhishek6280",
        database="Alzheimers"
    )
    print("Database connection successful")
except mysql.connector.Error as err:
    print("Error connecting to database:", err)
    exit(1)

# Get a cursor object to execute SQL queries
mycursor = mydb.cursor()

# Set background image
def get_base64(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def set_background(png_file):
    bin_str = get_base64(png_file)
    page_bg_img = '''
    <style>
    .stApp {
    background-image: url("data:image/png;base64,%s");
    background-position: center;
    background-size: cover;
    }
    </style>
    ''' % bin_str
    st.markdown(page_bg_img, unsafe_allow_html=True)

set_background('./images/bg4.png')

# Load the saved model
model = tf.keras.models.load_model('model.h5')

# Define the class labels
class_labels = ['Mild Demented', 'Moderate Demented', 'Non Demented', 'Very Mild Demented']

# Define the function to preprocess the image
def preprocess_image(image):
    image = image.convert('RGB')
    image = image.resize((176, 176))
    image = np.array(image)
    image = image / 255.0
    image = np.expand_dims(image, axis=0)
    return image

# Validate phone number and other inputs
def validate_phone_number(phone_number):
    pattern = r'^\d{10}$'
    contact = re.match(pattern, str(phone_number))
    if not contact:
        st.error('Please enter a 10 digit number!')
        return False
    return True

def validate_name(name):
    if not all(char.isalpha() or char.isspace() for char in name):
        st.error("Name should not contain numbers or special character.")
        return False
    return True

def validate_input(name, age, contact, file):
    if not name:
        st.error('Please enter the patient\'s name!')
        return False
    if not age:
        st.error('Please enter your age!')
        return False
    if not contact:
        st.error('Please enter your contact number!')
        return False
    if not file:
        st.error('Please upload the MRI scan!')
        return False
    return True

# Define the function to insert data into the database
def insert_data(name, age, gender, contact, prediction):
    try:
        sql = "INSERT INTO predictions (Patient_Name, Age, Gender, Contact, Prediction) VALUES (%s, %s, %s, %s, %s)"
        val = (name, age, gender, contact, prediction)
        mycursor.execute(sql, val)
        mydb.commit()
        print(mycursor.rowcount, "record inserted")
    except mysql.connector.Error as err:
        print("Error inserting record:", err)

# Main app function
def app():
    selected = option_menu(
        menu_title=None,
        options=["Home", "Alzheimer Detection", "About US"],
        icons=["house", "book", "envelope"],
        menu_icon="cast",
        default_index=0,
        orientation="horizontal",
    )

    if selected == 'Home':
        st.title("Alzheimer's Disease")
        st.write("Alzheimer disease is the most common type of dementia. It is a progressive disease beginning with mild memory loss and possibly leading to loss of the ability to carry on a conversation and respond to the environment. Alzheimer disease involves parts of the brain that control thought, memory, and language.")
        st.write("Using this website, you can find out if your MRI scan shows signs of Alzheimer's disease. It is classified according to four different stages of Alzheimer's disease.")
        st.write('1. Mild Demented')
        st.write("2. Very Mild Demented")
        st.write("3. Moderate Demented")
        st.write("4. Non Demented")

    elif selected == 'About US':
        st.title('Welcome!')
        st.write('This web app uses a CNN model to detect the presence of Alzheimer\'s disease in individuals of any age group. Instead of relying on traditional MRI scans, our portable web app provides a quick and efficient way to analyze medical images and generate reports instantly.')
        st.write('This web app is a Mini Project developed by Abhishek Sharma, Avantika Sharma, and Akashdeep Kaur.')

    elif selected == 'Alzheimer Detection':
        st.title('Alzheimer Detection Web App')
        st.write('Please enter your personal details along with the MRI scan.')

        with st.form(key='myform', clear_on_submit=True):
            name = st.text_input('Name')
            age = st.number_input('Age', min_value=1, max_value=150, value=40)
            gender = st.radio('Gender', ('Male', 'Female', 'Other'))
            contact = st.text_input('Contact Number', value='', key='contact')

            file = st.file_uploader('Upload an image', type=['jpg', 'jpeg', 'png'])
            submit = st.form_submit_button("Submit")

            if file is not None and validate_input(name, age, contact, file) and validate_phone_number(contact) and validate_name(name):
                st.success('Your personal information has been recorded.', icon="✅")
                image = Image.open(file)
                png_image = image.convert('RGBA')
                st.image(image, caption='Uploaded Image', width=200)

                st.write('Name:', name)
                st.write('Age:', age)
                st.write('Gender:', gender)
                st.write('Contact:', contact)

                image = preprocess_image(image)
                prediction = model.predict(image)
                prediction = np.argmax(prediction, axis=1)
                st.success('The predicted class is: ' + class_labels[prediction[0]])

                result_str = 'Name: {}\nAge: {}\nGender: {}\nContact: {}\nPrediction for Alzheimer: {}'.format(
                    name, age, gender, contact, class_labels[prediction[0]])

                insert_data(name, age, gender, contact, class_labels[prediction[0]])

                export_as_pdf = st.button("Export Report")

                def create_download_link(val, filename):
                    b64 = base64.b64encode(val)  # val looks like b'...'
                    return f'<a href="data:application/octet-stream;base64,{b64.decode()}" download="{filename}.pdf">Download file</a>'

                if export_as_pdf:
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_draw_color(0, 0, 0)
                    pdf.set_line_width(1)
                    pdf.rect(5.0, 5.0, 200.0, 287.0, 'D')

                    pdf.set_font('Times', 'B', 24)
                    pdf.cell(200, 20, 'Alzheimer Detection Report', 0, 1, 'C')

                    pdf.set_font('Arial', 'B', 16)
                    pdf.cell(200, 10, 'Patient Details', 0, 1)

                    pdf.set_font('Arial', '', 12)
                    pdf.cell(200, 10, f'Name: {name}', 0, 1)
                    pdf.cell(200, 10, f'Age: {age}', 0, 1)
                    pdf.cell(200, 10, f'Gender: {gender}', 0, 1)
                    pdf.cell(200, 10, f'Contact: {contact}', 0, 1)
                    pdf.ln(0.15)
                    pdf.ln(0.15)

                    png_file = "image.png"
                    png_image.save(png_file, "PNG")
                    pdf.cell(200, 10, 'MRI scan:', 0, 1)
                    pdf.image(png_file, x=40, y=80, w=50, h=50)

                    pdf.set_font('Arial', 'B', 16)
                    pdf.cell(200, 10, f'Prediction for Alzheimer: {class_labels[prediction[0]]}', 0, 1)
                    pdf.ln(2.0)

                    html = create_download_link(pdf.output(dest="S").encode("latin-1"), "test")
                    st.markdown(html, unsafe_allow_html=True)

# Run the app
if __name__ == '__main__':
    app()
