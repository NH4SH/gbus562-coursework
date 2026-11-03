## What I Built

PromptLab is a self-contained HTML tool for conversations with Anthropic's `claude-sonnet-5` model. It supports a system instruction, follow-up messages, separate conversations for each task, and unedited Markdown exports with the model name first and the required role headings. API keys are entered for the current page session and are not stored in files or included in exports. Four completed task conversations are saved in `runs/`: subscriber-perk ideas, bean cards, customer replies, and a pop-up location comparison. The location conversation preserves its original response, which reached the 1,200-token output limit, and a successful concise follow-up that finishes the calculations, applies the rent budget, and recommends Riverside Farmers Market. All five actual API responses remain recorded in the unedited exports and audit file.

## Why This Approach

Task 1 - Technique: zero-shot

Subscriber perks call for new ideas rather than imitation of a particular example, so this prompt uses no Brand Kit examples. It specifies the six-month subscriber audience, asks for exactly six numbered ideas, and limits each to one sentence and 25 words. The response produced six distinct suggestions within those limits, although its repeated “Consider” openings were repetitive.

Task 2 - Technique: one-shot

The bean cards need the house format rather than open-ended formatting, so the prompt supplies exactly one verbatim Huila card as its example. It separately lists the three new coffees' facts and explicitly requires the same labels in the same order. All three returned cards followed that structure while keeping the supplied roast, tasting-note, and brewing information.

Task 3 - Technique: few-shot

The customer replies need a consistent voice across a complaint, a product question, and a compliment, so the prompt supplies two verbatim Brand Kit exchanges. Those examples demonstrate constructive complaint handling and a brief appreciative response, while separate instructions require three numbered replies, no more than 40 words each, and no emoji. The returned replies met those format limits, but the late-order reply still assumed a promised delivery date, which shows that examples do not remove the need to check factual claims.

Task 4 - Technique: chain-of-thought

The location decision combines weekly visitors, purchase rates, average sales, a four-week duration, and a total rent constraint, so the prompt requests a concise step-by-step calculation and supplies all three locations' data. This makes the budget check and revenue-minus-rent comparison available to inspect instead of asking only for a location name. The first answer reached the token cap, so a follow-up requested a shorter completion; the final answer excluded Union Station's $8,000 rent and recommended Riverside with $6,480 in projected revenue minus rent. That comparison excludes other costs and is not a claim of net profit.

## Example Run

The complete Task 2 export follows verbatim.

claude-sonnet-5

### System

You are helping Wildframe Coffee Roasters, a fictional specialty coffee roaster selling beans online and through a monthly subscription. Its voice is warm, plainspoken, a little irreverent, and free of corporate jargon. Its audience is environmentally conscious urban professionals. Use only the business and product facts supplied in the user's task. Clearly distinguish proposed ideas from existing benefits or policies. Do not invent product availability, certifications, measured environmental outcomes, prices, delivery dates, guarantees, or customer experiences.

### You

Use this one house bean-card example as the format and voice pattern. Preserve the field labels and their order exactly:

HUILA, COLOMBIA
Roast: Medium
Tastes like: red apple, brown sugar, cocoa
Brew it: Pour-over or drip
Real talk: The coffee that converted our office's tea drinker. Mostly.

Create one new card for each of these coffees:
- Yirgacheffe, Ethiopia. Light roast. Notes: jasmine, lemon, bergamot. Best as pour-over.
- Cerrado, Brazil. Medium-dark roast. Notes: peanut, milk chocolate, low acidity. Good for espresso or French press.
- Chiapas, Mexico. Medium roast. Notes: almond, caramel, orange peel. Good for drip or AeroPress.

Required output: exactly three bean cards, separated by one blank line. Each card must start with the coffee's name and country in uppercase, followed by these identical labels in this exact order: Roast:, Tastes like:, Brew it:, Real talk:. Use the supplied facts for the first three labeled fields. Write a short, playful Real talk line without inventing customer experiences or additional product facts. Do not include the example card, an introduction, or any extra labels.

### Claude

YIRGACHEFFE, ETHIOPIA
Roast: Light
Tastes like: jasmine, lemon, bergamot
Brew it: Pour-over
Real talk: Floral enough to make you feel fancy before 8am.

CERRADO, BRAZIL
Roast: Medium-dark
Tastes like: peanut, milk chocolate, low acidity
Brew it: Espresso or French press
Real talk: Smooth, nutty, and unbothered. The golden retriever of coffees.

CHIAPAS, MEXICO
Roast: Medium
Tastes like: almond, caramel, orange peel
Brew it: Drip or AeroPress
Real talk: Cozy enough for a sweater, bright enough to wake you up anyway.

## Reflection

The bean cards were the clearest case of an example helping with the format. Each card used the same labels in the same order. The Real talk lines were playful, but the coffee facts stayed the same. For zero-shot, the six subscriber perks fit the word limit. Starting so many of them with “Consider” made the list repetitive, though. The few-shot customer replies were short and friendly. One detail I would change was in the late-order reply: it treated the delivery date as something Wildframe had promised. That needs checking before the reply goes to a customer. I am less sure whether this task needed two examples. I did not compare it with one example, so that would be my next test. Task 4 needed a follow-up because the first answer ran out of space. The completed answer picked Riverside, which had the strongest sales-minus-rent result within the budget. I would still check its wording: it said nearly five times, but the figures give 5.4 times the campus result.
