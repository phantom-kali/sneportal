# Voice Exam System Setup Guide

This guide will help you set up the Voice Exam System on your local machine. Follow these steps carefully.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Git

## Step 1: Clone the Repository

```bash
git clone https://github.com/phantom-kali/sneportal.git
cd sneportal
```

## Step 2: Set Up Python Virtual Environment

### For Windows:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate
```

### For macOS/Linux:
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

## Step 3: Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt
```

## Step 4: Set Up Google Cloud API

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - Cloud Text-to-Speech API
   - Cloud Speech-to-Text API
4. Create API Key:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "API Key"
   - Copy the generated API key

## Step 5: Configure Environment Variables

1. Create a `.env` file in the project root:
```bash
cp .env.example .env
```

2. Edit the `.env` file and add your Google API key:
```
GOOGLE_API_KEY=your_api_key_here
```

## Step 6: Database Setup

```bash
# Create database tables
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Populate sample exam data
python manage.py populate_exam_data
```

## Step 7: Run Development Server

```bash
# Start the development server
python manage.py runserver
```

The application should now be running at `http://127.0.0.1:8000/`

## Testing the Setup

1. Open your browser and go to `http://127.0.0.1:8000/`
2. Select an exam from the dropdown
3. Click "Start Voice Exam"
4. Allow microphone access when prompted
5. Follow the voice instructions

## Troubleshooting

### Microphone Issues
- Ensure your browser has permission to access your microphone
- Check if your microphone is working in your system settings

### API Key Issues
- Verify that the API key is correctly copied to the `.env` file
- Make sure both Text-to-Speech and Speech-to-Text APIs are enabled in Google Cloud Console
- Check if you have billing enabled for your Google Cloud project

### Database Issues
- If you get migration errors, try:
  ```bash
  python manage.py migrate --run-syncdb
  ```
- If sample data isn't loading, ensure you ran the populate_exam_data command

## Additional Configuration

### Voice Settings
You can adjust voice settings in `settings.py`:
- Speech rate
- Voice gender
- Language options

### Custom Exam Content
To add your own exam content:
1. Access the admin interface at `http://127.0.0.1:8000/admin/`
2. Create subjects, exams, and questions

## Support

If you encounter any issues:
1. Check the Django error logs
2. Verify all environment variables are set
3. Ensure all prerequisites are installed
4. Create an issue on the project repository

## Security Notes

- Never commit your `.env` file or API keys to version control
- Restrict your Google Cloud API key to only the necessary APIs
- Use strong passwords for admin access