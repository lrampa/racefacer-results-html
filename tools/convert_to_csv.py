import json
import csv
import sys
from datetime import datetime, timezone

def convert_timestamp_to_iso(timestamp, key):
    """Convert various timestamp formats to ISO format"""
    if not timestamp:
        return None
        
    try:
        # If it's already in ISO format, return as is
        if isinstance(timestamp, str) and 'T' in timestamp:
            return timestamp
            
        # Convert string timestamp to float if needed
        if isinstance(timestamp, str):
            timestamp = float(timestamp)

        # Create datetime object based on precision
        if key in ['current_lap_start_microtimestamp', 'last_passing']:
            # These fields contain millisecond timestamps
            dt = datetime.fromtimestamp(timestamp/1000, tz=timezone.utc)
            return dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + '+00:00'  # Format to milliseconds
        else:
            # Handle second-precision timestamps
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            return dt.strftime('%Y-%m-%dT%H:%M:%S+00:00')

    except (ValueError, TypeError):
        return timestamp

def flatten_json(json_obj, prefix=''):
    """Flatten nested JSON object with custom key prefixes"""
    items = []
    for key, value in json_obj.items():
        new_key = f"{prefix}{key}" if prefix else key
        
        if isinstance(value, dict):
            items.extend(flatten_json(value, f"{new_key}_").items())
        elif isinstance(value, list):
            continue
        else:
            # Convert timestamp fields to ISO format
            if key in ['timestamp', 'timestamp_socket', 'current_lap_start_timestamp', 
                      'current_lap_start_microtimestamp', 'last_passing']:
                value = convert_timestamp_to_iso(value, key)
            items.append((new_key, value))
    return dict(items)

def process_jsonl_to_csv(input_file, output_file):
    # Read first line to get structure
    with open(input_file, 'r') as f:
        first_line = json.loads(f.readline())
        
        # Flatten the top level and data level (excluding runs)
        top_level = flatten_json({k: v for k, v in first_line.items() if k != 'data'})
        data_level = flatten_json({k: v for k, v in first_line['data'].items() if k != 'runs'})
        
        # Get the runs data structure
        first_run = first_line['data']['runs'][0]
        run_level = flatten_json(first_run)
        
        # Combine all levels for fieldnames
        fieldnames = list(top_level.keys()) + list(data_level.keys()) + list(run_level.keys())
    
    # Write CSV
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        # Process all lines
        with open(input_file, 'r') as jsonfile:
            for line in jsonfile:
                data = json.loads(line)
                
                # Flatten top level (excluding data)
                top_data = flatten_json({k: v for k, v in data.items() if k != 'data'})
                
                # Flatten data level (excluding runs)
                data_fields = flatten_json({k: v for k, v in data['data'].items() if k != 'runs'})
                
                # Process each run in the data
                for run in data['data']['runs']:
                    # Combine all levels
                    row = {}
                    row.update(top_data)      # Add top level fields
                    row.update(data_fields)    # Add data level fields
                    row.update(flatten_json(run))  # Add run level fields
                    writer.writerow(row)

# Use the script
if __name__ == '__main__':
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'socketio/socketio.log'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'socketio/race_data_denormalized.csv'
    try:
        process_jsonl_to_csv(input_file, output_file)
        print(f"Successfully converted {input_file} to {output_file}")
    except Exception as e:
        print(f"An error occurred: {e}")
