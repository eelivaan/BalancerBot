# Extract the firmware into a binary file for download to Pico

with open("vl53l7cx_buffers.h", "r") as f:
    output_file = None
    i = 0
    for line in f:
        if "const uint8_t VL53L7CX_FIRMWARE[] = {" in line:
            #output_file = open("vl53l7cx_firmware.bin", "wb")
            pass
        elif "VL53L7CX_DEFAULT_CONFIGURATION" in line:
            output_file = open("vl53l7cx_default_config.bin", "wb")
            print("Opened vl53l7cx_default_config.bin for writing")
        elif "VL53L7CX_DEFAULT_XTALK" in line:
            output_file = open("vl53l7cx_default_xtalk.bin", "wb")
            print("Opened vl53l7cx_default_xtalk.bin for writing")
        elif "};" in line and output_file:
            output_file.close()
            print(f"Finished writing {output_file.name}")
            output_file = None
        elif output_file:
            # Remove comments and whitespace
            line = line.split("//")[0].strip()
            if line:
                if "VL53L7CX_FW_NBTAR_RANGING" in line:
                    line = line.replace("VL53L7CX_FW_NBTAR_RANGING", "0x01")  # Replace macro with actual value
                # Remove trailing commas and split by commas
                bytes_str = line.rstrip(",").split(",")
                # Convert to bytes and write to binary file
                output_file.write(bytes(int(b.strip(), 16) for b in bytes_str))
        i += 1
        if i % 3000 == 0:
            print(f"Processed {i} lines...")
    if output_file:
        output_file.close()
    print("Done")