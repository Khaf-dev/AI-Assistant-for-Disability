# Voice Commands Reference - Vision Assistant v1.1

Complete guide to all voice commands in Vision Assistant v1.1. Commands work in all 8 supported languages.

---

## Table of Contents

1. [Multi-Language Commands](#multi-language-commands)
2. [Face Recognition Commands](#face-recognition-commands)
3. [Audio & Obstacle Commands](#audio--obstacle-commands)
4. [Vision & Scene Commands](#vision--scene-commands)
5. [Navigation Commands](#navigation-commands)
6. [System Commands](#system-commands)

---

## Multi-Language Commands

Switch between 8 supported languages on-the-fly.

### Supported Languages

| Code | Language         | Notes              |
| ---- | ---------------- | ------------------ |
| en   | English          | Default            |
| id   | Indonesian       | Bahasa Indonesia   |
| es   | Spanish          | Español            |
| fr   | French           | Français           |
| de   | German           | Deutsch            |
| pt   | Portuguese       | Português (Brazil) |
| ja   | Japanese         | 日本語             |
| zh   | Mandarin Chinese | 中文               |

### Language Switching

- "Change language to Indonesian"
- "Switch to Spanish"
- "Speak French"
- "Set language to German"
- "Portuguese please"
- "Japanese" _(single word)_
- "Change to Chinese"
- "List available languages"

---

## Face Recognition Commands

### Enrollment (Learning Faces)

- "Enroll [name]"
- "Register [name]"
- "Register face as [name]"
- "Teach me the face of [name]"
- "Remember [name]"
- "Learn face of [name]"
- "Save face for [name]"

**Example:**

- User: "Enroll John"
- Assistant: "Preparing to enroll John. Please look at the camera."
- Response: "Successfully enrolled John. I will recognize you next time."

### Face Management

**List people:**

- "Who do you know?"
- "List known people"
- "Show my contacts"

**Remove people:**

- "Forget [name]"
- "Remove [name]"
- "Delete face of [name]"

**Statistics:**

- "Face statistics"
- "Enrollment status"
- "How many people do you know?"

**Recognition:**

- "Who is that?" _(when face detected)_
- "Recognize this face"
- "Who do I see?"

---

## Audio & Obstacle Commands

### Sound Detection

- "What do you hear?"
- "Listen"
- "Detect sounds"
- "Scan audio"
- "Monitor audio"

### Obstacle Detection

- "Check ahead"
- "Detect obstacles"
- "What's in my path?"
- "Obstacle detection"
- "Are there obstacles?"

### Sound Classification

- "Classify sound"
- "Identify sound"
- "What sound is that?"
- "Recognize this sound"
- "Analyze this sound"

### Audio Status

- "Audio statistics"
- "Audio status"
- "What audio options do you have?"

---

## Vision & Scene Commands

### Scene Description

- "Describe the scene"
- "What do you see?"
- "Describe my surroundings"
- "What's around me?"
- "What's in front of me?"

### Object Detection

- "Identify objects"
- "What objects are there?"
- "Detect objects"
- "Tell me about objects around me"

### Text Recognition

- "Read any text"
- "What text is visible?"
- "Read signs"
- "Recognize text"
- "What does it say?"

### Face Detection (General)

- "Detect faces"
- "Are there people around?"
- "How many faces?"
- "Who is nearby?"

---

## Navigation Commands

### Location & Directions

- "Where am I?"
- "What's my location?"
- "Current location"
- "Get my position"

### Navigation Assistance

- "Directions to [location]"
- "How do I get to [location]?"
- "Route to [location]"
- "Navigate to [location]"
- "Take me to [location]"

### Nearby Locations

- "What's nearby?"
- "Nearby restaurants"
- "Find a [type] nearby"
- "Nearest [location type]"

### Audio-Assisted Navigation

- "Guide me with audio"
- "Audio help"
- "Sound-guided navigation"
- "Help me navigate with sound"

### Guide Me Forward (real-time path + obstacles)

Combines the next route step (if you have an active route), obstacle check, and sound cues in one response.

- "Guide me forward"
- "Guide me"
- "What's ahead?"
- "Check path"
- "Is the path clear?"
- "Next direction"
- "Path clear"

*After you get directions to a place, say "Guide me forward" anytime to hear the current step plus any obstacles or sounds ahead.*

---

## System Commands

### Help & Information

- "Help"
- "What can you do?"
- "Show all commands"
- "List available commands"
- "What are my options?"
- "Help me"

### System Status

- "System status"
- "What's your status?"
- "Are all systems operational?"
- "Check all sensors"

### Control

- "Goodbye"
- "Bye"
- "Exit"
- "Quit"
- "Stop"
- "Turn off"
- "Shut down"
- "Close"

---

## Command Patterns

### Flexible Phrasing

The system recognizes these command patterns:

**Imperative:**

- "Enroll John"
- "Listen"
- "Check ahead"

**Question Form:**

- "Who do you know?"
- "What do you hear?"
- "Are there obstacles?"

**Natural Language:**

- "Can you listen?"
- "Would you check ahead?"
- "Can you describe the scene?"

**Short Form:**

- "Enroll"
- "Listen"
- "Check"

---

## Category Reference

| Category         | Count   | Example              |
| ---------------- | ------- | -------------------- |
| Multi-Language   | 10+     | "Switch to Spanish"  |
| Face Recognition | 20+     | "Enroll John"        |
| Audio/Obstacles  | 15+     | "What do you hear?"  |
| Vision           | 15+     | "Describe the scene" |
| Navigation       | 15+     | "Where am I?"        |
| System           | 20+     | "Goodbye"            |
| **Total**        | **95+** | -                    |

---

## Tips for Best Results

1. **Speak Clearly:** Enunciate language names and names distinctly
2. **Pause After:** Wait for system acknowledgment before next command
3. **Context Matters:** Commands work in active mode (after app startup)
4. **Multi-Step:** Enroll face, then ask "Who do you know?" for confirmation
5. **Audio Quality:** Use quiet environment for speech recognition
6. **Microphone:** Position microphone 15-30cm away from speaker

---

## Error Handling

If command not recognized:

| Error                        | Solution                                   |
| ---------------------------- | ------------------------------------------ |
| "Could not understand audio" | Speak louder/clearer                       |
| "Language not supported"     | Check language code (en, id, es, etc.)     |
| "No faces detected"          | Ensure adequate lighting during enrollment |
| "Audio system not available" | Check microphone connection                |
| "Person not found"           | Use exact enrolled name                    |

---

## Accessibility Notes

- **Voice-Only Interface:** No visual confirmation required
- **Audio Feedback:** All responses are spoken aloud
- **Multilingual:** Commands work in user's selected language
- **Error Messages:** Clear spoken feedback for misunderstandings
- **Confirmation:** System confirms important actions

---

## Examples by Workflow

### Workflow 1: Day Start

1. "(App starts)"
2. "Switch to Indonesian"
3. "Who do you know?" _(verify enrollment)_
4. "Where am I?" _(check location)_
5. "What do you see?" _(initial scene)_

### Workflow 2: Meeting Someone

1. "What do you hear?"
2. "Check ahead"
3. "Any faces?"
4. "Recognize this face"

### Workflow 3: Navigation

1. "Directions to library"
2. "Audio help"
3. "What do you hear?"
4. "Check ahead" _(monitor obstacles)_
5. "Navigate forward"

### Workflow 4: Face Training

1. "Enroll John"
2. "Look at camera" _(user positions self)_
3. "Successfully enrolled"
4. "Remember Sarah" _(enroll another)_
5. "Who do you know?" _(verify both)_

---

## Version Information

- **Version:** 1.1.0
- **Release Date:** February 11, 2026
- **Languages:** 8 (EN, ID, ES, FR, DE, PT, JA, ZH)
- **Command Count:** 95+
- **Status:** Stable

Last Updated: February 11, 2026
