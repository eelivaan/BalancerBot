#include <Wire.h>
#include <MPU6050.h>
#include "sensortest.h"
#include "motors.h"

MPU6050 mpu;
bool bReadSensor = false;
bool bEnablePID = false;
float tgt = -0.24;
const float Kp = 5.0;
const float Kd = 0.0;
float prev_e = 0.0;

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
  pinMode(IB1_PIN, OUTPUT);
  pinMode(IB2_PIN, OUTPUT);

  tgt = mpu.getAccelerationX() / 16384.0;

  /*pinMode(2, OUTPUT);
  pinMode(3, OUTPUT);
  analogWrite(2, 255);
  analogWrite(3, 0);*/
}

float calcPID()
{
  int16_t AcX = mpu.getAccelerationX();
  float e = tgt - AcX / 16384.0;
  float de = e - prev_e;
  prev_e = e;
  return Kp * e + Kd * de;
}

void loop()
{
  if (bReadSensor)
  {
    int16_t ax, ay, az, gx, gy, gz;

    mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);

    Serial.print("Accel: ");
    float Ax = ax / 16384.0;
    float Ay = ay / 16384.0;
    float Az = az / 16384.0;
    Serial.print(String(Ax) + ", " + String(Ay) + ", " + String(Az) + " | ");
    float Rx = mpu.getRotationX();
    float Ry = mpu.getRotationY();
    float Rz = mpu.getRotationZ();
    Serial.print(String(Rx) + ", " + String(Ry) + ", " + String(Rz));
    Serial.println();

    delay(1000);
  }
  
  if (bEnablePID)
  {
    /*for (int i = 0; i < 255; i += 50)
    {
      analogWrite(IA1_PIN, i);
      Serial.print(String(i) + " ");
      delay(3000);
    }*/
    const float signal = calcPID();

    const int pwm = min(100 + abs(signal) * 155, 255);
    Serial.println(pwm);

    analogWrite(IA1_PIN, signal > 0.0 ? pwm : 0);
    analogWrite(IA2_PIN, signal > 0.0 ? 0 : pwm);

    analogWrite(IB1_PIN, signal < 0.0 ? pwm : 0);
    analogWrite(IB2_PIN, signal < 0.0 ? 0 : pwm);
  }

  delay(50);
}
