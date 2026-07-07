Movie getMovieForEmotion(String emotion) {
  String normalizedEmotion = normalizeEmotion(emotion);
  if (normalizedEmotion.equals("sad")) return sadMovie;
  if (normalizedEmotion.equals("neutral")) return neutralMovie;
  return happyMovie;
}

String normalizeEmotion(String emotion) {
  if (emotion == null) return "happy";
  String normalizedEmotion = emotion.toLowerCase();
  if (normalizedEmotion.equals("sad")) return "sad";
  if (normalizedEmotion.equals("angry")) return "sad";
  if (normalizedEmotion.equals("neutral")) return "neutral";
  return "happy";
}

String indoorEmotionFromMessage(OscMessage msg) {
  if (msg.arguments().length >= 4) {
    return normalizeEmotion(msg.get(3).stringValue());
  }
  return "happy";
}
