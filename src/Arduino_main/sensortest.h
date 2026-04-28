
void findMPU6050() {
  //Wire.begin();
  //Serial.begin(9600);
  Serial.println("Scanning I2C addresses...");
  
  // Try 0x68 (AD0 = LOW)
  Wire.beginTransmission(0x68);
  if (Wire.endTransmission() == 0) {
    Serial.println("MPU6050 found at 0x68!");
  }
  
  // Try 0x69 (AD0 = HIGH)
  Wire.beginTransmission(0x69);
  if (Wire.endTransmission() == 0) {
    Serial.println("MPU6050 found at 0x69!");
  }
}