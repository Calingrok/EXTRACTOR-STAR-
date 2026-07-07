# Python का एक छोटा और स्टेबल वर्शन इस्तेमाल करें
FROM python:3.10-slim

# वर्किंग डायरेक्टरी सेट करें
WORKDIR /app

# पहले requirements कॉपी करें (फास्ट बिल्ड के लिए)
COPY requirements.txt .

# लाइब्रेरी इंस्टॉल करें
RUN pip install --no-cache-dir -r requirements.txt

# बाकी कोड कॉपी करें
COPY . .

# बोट स्टार्ट करें
CMD ["python3", "main.py"]
