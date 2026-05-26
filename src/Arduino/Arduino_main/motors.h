#define IA1_PIN 9
#define IA2_PIN 10
#define IB1_PIN 5
#define IB2_PIN 6

void forward()
{
  digitalWrite(IA1_PIN, HIGH);
  digitalWrite(IA2_PIN, LOW);
}

void backward()
{
  digitalWrite(IA1_PIN, LOW);
  digitalWrite(IA2_PIN, HIGH);
}

void stop()
{
  digitalWrite(IA1_PIN, LOW);
  digitalWrite(IA2_PIN, LOW);
}