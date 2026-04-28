#include <Wire.h>
#include <MPU6050.h>
#include "sensortest.h"
#include "motors.h"

MPU6050 mpu;
bool bReadSensor = true;

void setup()
{
  Wire.begin();
  Serial.begin(115200);

  // gyro sensor
  findMPU6050();

  mpu.initialize();

  if (mpu.testConnection())
  {
    Serial.println("MPU6050 connected!");
    bReadSensor = true;
  }
  else
  {
    Serial.println("No connection :(");
  }

  // motor control
  pinMode(IA1_PIN, OUTPUT);
  pinMode(IA2_PIN, OUTPUT);

  digitalWrite(IA1_PIN, HIGH);
  digitalWrite(IA2_PIN, LOW);
}

void loop()
{
  if (bReadSensor)
  {
    int16_t ax, ay, az, gx, gy, gz;

    mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);

    Serial.print("Accel: ");
    Serial.print(String(ax) + ", " + String(ay) + ", " + String(az) + " | ");
    Serial.print(String(mpu.getRotationX()) + ", " + String(mpu.getRotationY()) + ", " + String(mpu.getRotationZ()));
    Serial.println();

    delay(1000);
  }
  else
  {
    for (int i = 0; i < 255; i += 50)
    {
      analogWrite(IA1_PIN, i);
      Serial.print(String(i) + " ");
      delay(3000);
    }
  }
}
