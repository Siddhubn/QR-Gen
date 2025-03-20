# QR Code Generator - Flask App

## Overview
This Flask application allows users to generate **QR codes** from text input. The user enters text into a web form, and upon submission, a **QR code image is generated and downloaded**.

## Features
- Simple **Flask-based web app** with a user-friendly interface.
- Generates **QR codes dynamically** using the `qrcode` library.
- Users can **download** the generated QR code as a PNG image.
- **Modern UI** with a dark-themed design and animated background elements.

## Prerequisites
Ensure you have Python and the required libraries installed:
```bash
pip install flask qrcode
```

## Project Structure
```
QR_Code_Gen/

```

## Usage
1. Run the Flask application:
   ```bash
   python app.py
   ```
2. Open your browser and go to `http://127.0.0.1:5000/`.
3. Enter text and click **Generate QR Code**.
4. The QR code will be generated and downloaded automatically.

## Issues & Improvements
- **Security Enhancement**: Currently, there is no input validation. It is recommended to add validation and sanitization for user input.
- **Customization Options**: Allow users to select **QR code colors, sizes, or formats**.
- **Real-time QR Preview**: Display the QR code on the webpage before downloading.

## Contributions
Feel free to contribute by adding features, fixing bugs, or improving UI elements.

## License
This project is open-source under the MIT License.

