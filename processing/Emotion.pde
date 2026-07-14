PImage getImageForEmotion(String emotion) {
  String normalizedEmotion = normalizeEmotion(emotion);
  if (normalizedEmotion.equals("sad")) return sadImage;
  if (normalizedEmotion.equals("neutral")) return neutralImage;
  if (normalizedEmotion.equals("angry")) return angryImage;
  return happyImage;
}

String normalizeEmotion(String emotion) {
  if (emotion == null) return "happy";
  String normalizedEmotion = emotion.toLowerCase();
  if (normalizedEmotion.equals("sad")) return "sad";
  if (normalizedEmotion.equals("angry")) return "angry";
  if (normalizedEmotion.equals("neutral")) return "neutral";
  return "happy";
}

String indoorEmotionFromMessage(OscMessage msg) {
  if (msg.arguments().length >= 4) {
    return normalizeEmotion(msg.get(3).stringValue());
  }
  return "happy";
}
