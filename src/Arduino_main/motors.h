#define IA1_PIN 9
#define IA2_PIN 10

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