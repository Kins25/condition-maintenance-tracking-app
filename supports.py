import pandas as pd
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

#Set up of Email notification system 
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "kinsyoung@gmail.com"
SENDER_PASSWORD = "kklaxncjoqxbgtrl"

def sendEmail(recipient, subject, message):
    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(message, "plain"))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("📧 Email sent successfully.")

    except Exception as e:
        import traceback
        print("📫 Failed to send email.")
        traceback.print_exc()

# Loading Most Current Machine Data 
def loadLatestMachineData():
    try:
        if not os.path.exists("machines.csv"):
            return None
        df = pd.read_csv("machines.csv")
        return df.groupby("machine_id").tail(1).sort_values("machine_id")
    except Exception as e:
        print(f"Error loading machine data: {e}")
        return None

#Loading Most Recent Machines Data for Tracking past Components Changed
def loadRecentMachineData(minutes=.2):
    if not os.path.exists("machines.csv"):
        return None
    df = pd.read_csv("machines.csv", parse_dates=["timestamp"])
    cutoff = pd.Timestamp.now() - pd.Timedelta(minutes=minutes)
    return df[df["timestamp"] >= cutoff]

#Get Inventory of Machines
def loadInventory():
    try:
        return pd.read_csv("machines_inventory.csv")
    except Exception as e:
        print(f"Error loading inventory: {e}")
        return pd.DataFrame()

# Define Users & Login
def loadUserDb():
    try:
        df = pd.read_csv("users.csv", index_col=0)
        return df.to_dict("index")
    except Exception as e:
        print(f"Error loading users.csv: {e}")
        return {}

def validateLogin(username, password):
    users = loadUserDb()
    return username in users and users[username]["password"] == password

# Define Maintenance Tasks to be performed
def loadMaintenanceTasks():
    latest = loadLatestMachineData()
    maintenance = {}
    if latest is None:
        return maintenance

    for i in range(1, 11):
        partFile = f"wearing_parts_machine_{i}.csv"
        if os.path.exists(partFile):
            try:
                df = pd.read_csv(partFile, encoding='ISO-8859-1')
                df.columns = df.columns.str.strip().str.replace('\xa0', '', regex=True)
                if df.columns[1] != 'Article Number':
                    df.rename(columns={df.columns[1]: 'Article Number'}, inplace=True)

                currentHours = float(latest[latest["machine_id"] == i]["cumulative_hours"].values[0])

                def hoursLeft(row):
                    try:
                        timeToReplace = float(row["Time to replacement"])
                        if pd.isna(row["Last Replacement"]) or row["Last Replacement"] == "":
                            return timeToReplace - currentHours
                        else:
                            lastReplace = float(row["Last Replacement"])
                            return (lastReplace + timeToReplace) - currentHours
                    except:
                        return float("inf")

                df["Hours Left"] = df.apply(hoursLeft, axis=1)
                due = df[df["Hours Left"] < 100]

                expectedCols = ["Article Number", "Name", "Qty", "Manufacturer"]
                existingCols = [col for col in expectedCols if col in due.columns]

                if existingCols:
                    maintenance[i] = due[existingCols + ["Hours Left"]]
            except Exception as e:
                print(f"Error processing {partFile}: {e}")
    return maintenance

# Confirm & Approve Maintenance Tasks performed
def confirmMaintenanceTask(machine_id, article_number):
    file = f"wearing_parts_machine_{machine_id}.csv"
    try:
        df = pd.read_csv(file, encoding='ISO-8859-1')
        df.columns = df.columns.str.strip().str.replace('\xa0', '', regex=True)
        if df.columns[1] != 'Article Number':
            df.rename(columns={df.columns[1]: 'Article Number'}, inplace=True)
        latest = loadLatestMachineData()
        curHours = float(latest[latest["machine_id"] == machine_id]["cumulative_hours"].values[0])
        df.loc[df["Article Number"] == article_number, "Last Replacement"] = curHours
        df.to_csv(file, index=False, encoding='ISO-8859-1')
    except Exception as e:
        print(f"Error confirming maintenance task: {e}")

def generatePendingReport():
    tasks = loadMaintenanceTasks()
    report = []
    for mid, df in tasks.items():
        if not df.empty:
            df = df.copy()
            df["Machine ID"] = mid
            report.append(df)
    #Report Machine number and components due for replacement
    reportDF = pd.concat(report) if report else pd.DataFrame(columns=["Machine ID", "Article Number", "Name", "Qty", "Manufacturer", "Hours Left"])
    fName = f"pending_maintenance_{datetime.now().strftime('%Y%m%d')}.csv"
    reportDF.to_csv(fName, index=False)
    return fName

def generateCompletedReport():
    from datetime import datetime
    today = datetime.now().date()
    completed = []

    # Load latest cumulative hours for each machine
    latestData = loadLatestMachineData()
    if latestData is None:
        return None

    for i in range(1, 11):
        file = f"wearing_parts_machine_{i}.csv"
        if os.path.exists(file):
            try:
                df = pd.read_csv(file, encoding='ISO-8859-1')
                df.columns = df.columns.str.strip().str.replace('\xa0', '', regex=True)

                if df.columns[1] != 'Article Number':
                    df.rename(columns={df.columns[1]: 'Article Number'}, inplace=True)

                df["Last Replacement"] = pd.to_numeric(df["Last Replacement"], errors="coerce")

                # Get machine cumulative hours
                curHours = float(latestData[latestData["machine_id"] == i]["cumulative_hours"].values[0])

                # Querry and report any parts replaced within last 1 month in all machines
                recent = df[df["Last Replacement"].between(curHours -720, curHours)]

                if not recent.empty:
                    recent["Machine ID"] = i
                    recent["Replacement Timestamp"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    selected = recent[[
                        "Machine ID", "Article Number", "Name", "Qty", "Manufacturer", "Replacement Timestamp"
                    ]]
                    completed.append(selected)

            except Exception as e:
                print(f"❌ Error processing completed for machine {i}: {e}")

    if completed:
        reportDF = pd.concat(completed)
        fName = f"completed_maintenance_{datetime.now().strftime('%Y%m%d')}.csv"
        reportDF.to_csv(fName, index=False)
        return fName
    return None
