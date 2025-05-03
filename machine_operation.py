import asyncio
import random
import datetime
import csv
import io
import platform
import os

def loadMachineStates():
    #Check and load last known machine stats 
    if not os.path.exists("machines.csv"):
        return [
            {
                "machine_id": i,
                "status": "running",
                "temperature": 70.0,
                "vibration": 0.5,
                "rpm": 1000,
                "cumulative_hours": random.uniform(650, 800),
                "daily_hours": 0.0,
                "last_update_date": datetime.datetime.now().date()
            }
            for i in range(1, 11)
        ]
    
    machines = {}
    with open("machines.csv", "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            machine_id = int(row["machine_id"])
            machines[machine_id] = {
                "machine_id": machine_id,
                "status": row["status"],
                "temperature": float(row["temperature"]),
                "vibration": float(row["vibration"]),
                "rpm": float(row["rpm"]),
                "cumulative_hours": float(row["cumulative_hours"]),
                "daily_hours": float(row["daily_hours"]),
                "last_update_date": datetime.datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S").date()
            }
    
    # Initialize all 10 Machines
    return [machines.get(i, {
        "machine_id": i,
        "status": "running",
        "temperature": 70.0,
        "vibration": 0.5,
        "rpm": 1000,
        "cumulative_hours": random.uniform(650, 800),
        "daily_hours": 0.0,
        "last_update_date": datetime.datetime.now().date()
    }) for i in range(1, 11)]

# Initialize and create .csv file if it does not exist
header = ["machine_id", "status", "temperature", "vibration", "rpm", "timestamp", "cumulative_hours", "daily_hours"]

def initializeFile():
    if not os.path.exists("machines.csv"):
        with open("machines.csv", "w", newline="") as f:
            csvWriter = csv.writer(f)
            csvWriter.writerow(header)

# Using probability of 80% machines running, 16% Idle, and 4% in Error
def updateMachineStatus():
    rand = random.random()
    if rand < 0.80:
        return "running"
    elif rand < 0.96:  # 0.80 + 0.16
        return "idle"
    else:
        return "error"

# Update Machine Data
async def updateMachines():
    output = io.StringIO()
    csvWriter = csv.writer(output)
    csvWriter.writerow(header)
    
    # Load machine states
    machines = loadMachineStates()
    
    # Initialize machine.csv file
    if platform.system() != "Emscripten":
        initializeFile()

    while True:  # Run indefinitely
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rows = []
        for machine in machines: 
            machine["status"] = updateMachineStatus()
            
            # Update metrics based on status
            if machine["status"] == "running":
                # Temperature fluctuates between 60-300°C
                machine["temperature"] += random.uniform(-50, 100)
                machine["temperature"] = max(60, min(300, machine["temperature"]))
                
                # Vibration range between 0-0.9
                machine["vibration"] += random.uniform(-0.05, 0.5)
                machine["vibration"] = max(0, min(0.9, machine["vibration"]))
                
                # RPM operating range between 0-20000
                machine["rpm"] += random.uniform(-1000, 1000)
                machine["rpm"] = max(0, min(20000, machine["rpm"]))
                
                # Increment cumulative hours every 10 seconds
                today = datetime.datetime.now().date()
                if machine["last_update_date"] != today:
                    machine["daily_hours"] = 0.0
                    machine["last_update_date"] = today

                increment = 10 / 3600 
                if machine["daily_hours"] + increment <= 24:
                    machine["cumulative_hours"] += increment
                    machine["daily_hours"] += increment
                else:
                    machine["status"] = "idle"
                    machine["temperature"] = 60.0
                    machine["vibration"] = 0.2
                    machine["rpm"] = 0
            
            # Set minimum values for Idle and Error State
            else:
                machine["temperature"] = 60.0
                machine["vibration"] = 0.2
                machine["rpm"] = 0
            
            # Prepare row data
            row = [
                machine["machine_id"],
                machine["status"],
                round(machine["temperature"], 2),
                round(machine["vibration"], 2),
                round(machine["rpm"]),
                timestamp,
                round(machine["cumulative_hours"], 2),
                round(machine["daily_hours"], 2)
            ]
            rows.append(row)
        
        # Write to machines.csv file
        if platform.system() != "Emscripten":
            with open("machines.csv", "a", newline="") as f:
                fileWriter = csv.writer(f)
                for row in rows:
                    fileWriter.writerow(row)
        
        for row in rows:
            csvWriter.writerow(row)
        
        # Update every 10 seconds
        await asyncio.sleep(10)
    
    csv_content = output.getvalue()
    output.close()
    print(csv_content)

# Function Read Machine Data.
async def main():
    
    await updateMachines()

if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())
