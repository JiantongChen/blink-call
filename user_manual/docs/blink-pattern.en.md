# Blink Pattern

Blink pattern settings determine which eye-open and eye-closed actions the patient needs to complete before a call alert is triggered.

## What Is a Blink Sequence?

A blink sequence is a series of eye-open and eye-closed actions.

The software recognizes the actions in the configured order. After all actions are completed, it triggers the call alert.

![Blink call](https://cdn.jsdelivr.net/gh/JouleEmbodiedAILab/blink-call@main/user_manual/docs/images/quick-start-call-alert.gif)

## Default Blink Sequence

The default sequence is:

Eyes open for 1.5 seconds -> eyes closed for 1 second -> eyes open for 1 second -> eyes closed for 1.5 seconds.

This sequence is longer than a natural blink, which helps reduce accidental triggering.

## Modify the Blink Sequence

Path:

Settings -> Blink Call -> Blink Sequence.

You can change the action type and duration of each step.

![Modify blink sequence](https://cdn.jsdelivr.net/gh/JouleEmbodiedAILab/blink-call@main/user_manual/docs/images/blink-pattern-settings.jpg)

## Add or Remove Action Steps

Click [Add Step] to add a new eye-open or eye-closed action.

If the sequence has multiple steps, you can delete steps that are not needed.

![Add or remove actions](https://cdn.jsdelivr.net/gh/JouleEmbodiedAILab/blink-call@main/user_manual/docs/images/blink-pattern-settings.gif)

## Choose a Suitable Duration

Each step can be set from 0.5 seconds to 5 seconds.

Start with the default settings first, then adjust them according to the patient's actual ability.

## Suggestions

- If closing the eyes is difficult for the patient, shorten the eye-closed duration appropriately.
- If the alert is triggered when the patient did not mean to call, add more action steps or slightly increase the duration.
- Avoid making the sequence too long, so the patient does not become tired while completing it.
- Avoid using only a very short eye-closed action, because it may be confused with a natural blink.
