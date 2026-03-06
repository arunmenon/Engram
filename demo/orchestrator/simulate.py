"""
PayPal Persona Simulation — E2E Graph Population & Context Validation.

Drives the orchestrator API to simulate 7 personas × N sessions × M turns,
then analyzes the resulting graph and demonstrates context-aware retrieval.

Usage:
    python -m demo.orchestrator.simulate                          # Run full simulation
    python -m demo.orchestrator.simulate --sessions 3 --turns 5   # Fewer sessions/turns
    python -m demo.orchestrator.simulate --analyze                # Graph analysis only
    python -m demo.orchestrator.simulate --context-demo           # Returning customer demo
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import random
import sys
import time
import uuid
from datetime import datetime, timezone

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("simulate")

ORCHESTRATOR_URL = os.environ.get("ORCHESTRATOR_URL", "http://localhost:8100")
CG_API_URL = os.environ.get("CG_API_URL", "http://localhost:8000")

# ---------------------------------------------------------------------------
# Persona conversation scripts
# ---------------------------------------------------------------------------
# Each persona has 10 session topics. Each topic has an opener + follow-up turns.

PERSONA_SCRIPTS: dict[str, list[dict]] = {
    "billing_dispute": [
        {
            "opener": "Hi, I was charged twice for my team's Pro subscription this month. Transaction IDs are TXN-9182 and TXN-9183, both for $49.99 on Feb 3rd.",
            "turns": [
                "Can you look up both transaction IDs and confirm they're duplicates?",
                "Yes, I only authorized one payment. The second one appeared about 10 minutes after the first.",
                "I'd like a full refund on TXN-9183 please. How long will it take?",
                "Will my subscription stay active during the refund process?",
                "Can you also email me a confirmation of the refund for my records?",
            ],
        },
        {
            "opener": "I cancelled my Pro subscription last week but I just got charged $49.99 again today. Order REF-4421.",
            "turns": [
                "I cancelled through the account settings page on January 28th. Didn't get a confirmation email though.",
                "Can you check if the cancellation actually went through on your end?",
                "So it wasn't processed? That's frustrating. I need a refund for this charge.",
                "How do I make sure the subscription is fully cancelled this time?",
                "Please send me a cancellation confirmation email when it's done.",
            ],
        },
        {
            "opener": "We just got hit with a price increase from $49.99 to $69.99 per month without any notice. Is this right?",
            "turns": [
                "I've been on this plan for 14 months. When was the price change announced?",
                "I checked my email and didn't receive anything about this. Can you verify?",
                "Is there any way to keep the old pricing? We're a small engineering team.",
                "What about an annual plan — would that lock in a better rate?",
                "Can you apply the annual pricing starting from this billing cycle?",
            ],
        },
        {
            "opener": "I need to add billing manager permissions for my colleague, but I can't find the option in the dashboard.",
            "turns": [
                "I'm the account owner. Her email is jliu@example.com.",
                "I only want her to manage invoices and payment methods, not full admin access.",
                "Does she need her own PayPal account to get billing access?",
                "What's the difference between billing manager and financial admin roles?",
                "OK, let's go with billing manager. Can you walk me through the steps?",
            ],
        },
        {
            "opener": "There's a discrepancy on our invoice. The subtotal says $49.99 but we were charged $53.74.",
            "turns": [
                "We're based in Oregon — there shouldn't be sales tax on digital services here.",
                "Can you break down exactly what the $3.75 difference is for?",
                "If it's a processing fee, that wasn't disclosed when we signed up.",
                "I need a corrected invoice for our accounting team. Can you issue one?",
                "Going forward, will there be any additional fees beyond the subscription price?",
            ],
        },
        {
            "opener": "I just upgraded from Basic to Pro mid-cycle. Can you explain how the proration works?",
            "turns": [
                "I upgraded on February 10th and my billing cycle renews on March 1st.",
                "So I'm paying the difference for the remaining 19 days?",
                "The charge I see is $37.42. Does that math check out?",
                "Will my next full billing cycle charge be the standard $49.99?",
                "Can I get an itemized receipt showing the proration calculation?",
            ],
        },
        {
            "opener": "Our subscription auto-renewal failed and now the whole team is locked out. We need this fixed ASAP.",
            "turns": [
                "The card on file is valid — I just used it for another purchase. Maybe it's the expiry date?",
                "The card expires 03/2026 but the one on file might show the old expiry 01/2025.",
                "OK I've updated the card details. Can you retry the payment now?",
                "How long until the team gets access back after payment goes through?",
                "Can you set up a backup payment method so this doesn't happen again?",
            ],
        },
        {
            "opener": "I think there's a tax calculation error on my international billing. I'm in Canada but being charged US tax.",
            "turns": [
                "My business is registered in Ontario, Canada. GST/HST should apply, not US sales tax.",
                "Our business number is 12345 6789 RT0001. Can you update the tax settings?",
                "I need corrected invoices for the last 3 months showing the right tax treatment.",
                "Will future invoices automatically use the Canadian tax rate?",
                "Can you also add our company name 'ChenTech Solutions' to the billing profile?",
            ],
        },
        {
            "opener": "We have three separate subscriptions and I'd like to consolidate them into one invoice.",
            "turns": [
                "The accounts are team-alpha@example.com, team-beta@example.com, and team-gamma@example.com.",
                "All three are Pro plans. Can they all bill to the same payment method?",
                "I'd prefer a single consolidated monthly invoice rather than three separate charges.",
                "Is there a volume discount if we're paying for 3 team plans?",
                "Can all three be set to the same billing date — say the 1st of each month?",
            ],
        },
        {
            "opener": "I need to export our complete billing history for an internal audit. How do I get that?",
            "turns": [
                "We need everything from January 2024 to present, including all invoices and receipts.",
                "Is there a way to export as CSV or PDF? Our finance team needs both formats.",
                "The dashboard only shows the last 6 months. How do I get older records?",
                "Can you include transaction IDs and payment method details in the export?",
                "How long does PayPal retain billing records? We need to keep them for 7 years.",
            ],
        },
    ],
    "payment_failure": [
        {
            "opener": "My card keeps getting declined when I try to pay an invoice. Error code PP-1042.",
            "turns": [
                "It's a Visa debit card. I've used it with PayPal before without issues.",
                "I just checked with my bank and they say there are no blocks on the card.",
                "The invoice amount is $1,250. Could it be a transaction limit issue?",
                "Can I split the payment across two methods — part card, part PayPal balance?",
                "OK, I'll try adding a different card. What card types do you accept?",
            ],
        },
        {
            "opener": "A client sent me $800 through PayPal but it's showing as 'pending' for 3 days now.",
            "turns": [
                "My account is verified and I've received payments before. This is unusual.",
                "The sender said the money left their account. Where is it?",
                "Could this be related to my account being flagged for review?",
                "I need this money to pay my own invoices by Friday. Any way to speed it up?",
                "If it doesn't clear by tomorrow, can you escalate this?",
            ],
        },
        {
            "opener": "I accidentally sent $500 to the wrong PayPal email address. Can you help me get it back?",
            "turns": [
                "I sent it to janedoe@gmail.com but it should have been janedoe@example.com.",
                "The payment was sent about 2 hours ago. Has it been claimed yet?",
                "If they haven't claimed it, can you cancel the transaction?",
                "What happens if they've already claimed the money?",
                "I'll send the correct amount to the right address now. Can you watch for duplicates?",
            ],
        },
        {
            "opener": "PayPal keeps asking me to verify my identity every time I try to make a payment. It's been 2 weeks.",
            "turns": [
                "I've uploaded my driver's license three times already. Each time it says 'under review'.",
                "I'm a freelance designer and I can't receive client payments until this is resolved.",
                "Is there another form of ID I can use? Maybe a passport?",
                "How long does verification normally take?",
                "Can you check the status of my verification right now?",
            ],
        },
        {
            "opener": "I set up automatic payments for my rent but it failed this month and now I have a late fee.",
            "turns": [
                "The auto-pay was scheduled for Feb 1st. I had sufficient balance.",
                "The error message just says 'payment could not be processed'. Nothing specific.",
                "My landlord uses PayPal.me for rent collection. Has anything changed on their end?",
                "Can PayPal cover the late fee since the failure was on your system's side?",
                "How do I make sure this doesn't happen next month?",
            ],
        },
        {
            "opener": "I'm trying to pay a vendor in euros but PayPal won't let me select EUR as currency.",
            "turns": [
                "My account is USD-based. I want to send EUR 2,000 to a German vendor.",
                "What exchange rate will PayPal use? Is it the market rate?",
                "The vendor says they'll get less than EUR 2,000 if PayPal converts. Can I avoid that?",
                "Can I add a EUR balance to my PayPal account directly?",
                "What about using PayPal's mass payments for regular EUR payments?",
            ],
        },
        {
            "opener": "My client's payment is stuck in a 'review' state and I need to refund them so they can resend it.",
            "turns": [
                "The payment was for $3,200 for a logo design project. It's been in review for 5 days.",
                "I've completed the work already. Can you just release the payment instead?",
                "What information do you need from me to speed up the review?",
                "Is this happening because the amount is larger than my usual transactions?",
                "If you release this one, will my future payments also get reviewed?",
            ],
        },
        {
            "opener": "I got a notification that my bank account was removed from PayPal. I didn't do this.",
            "turns": [
                "The bank account has been linked for 2 years. Why would it suddenly be removed?",
                "I need to re-add it but it's saying the account is already linked to another PayPal account.",
                "I definitely don't have another PayPal account. This must be an error.",
                "Can you check if someone else added my bank details to their account?",
                "This is really concerning from a security standpoint. Should I change my passwords?",
            ],
        },
        {
            "opener": "PayPal charged me a fee on a 'friends and family' payment. I thought those were free.",
            "turns": [
                "I sent $200 to my sister using the friends and family option.",
                "The fee was $5.80. I've never been charged for personal payments before.",
                "Could it be because she's in a different country? She's in the UK.",
                "Is there a way to avoid fees on international personal transfers?",
                "Can you refund the fee this time since I wasn't aware of the international charge?",
            ],
        },
        {
            "opener": "I'm getting a 'payment method not supported' error when trying to use my prepaid Visa gift card.",
            "turns": [
                "It's a $200 Visa gift card I received as a birthday present.",
                "The card works at regular stores. Why won't PayPal accept it?",
                "I registered the card online with my billing address. What else do I need?",
                "Is there any workaround to use prepaid cards with PayPal?",
                "If not, can I load the card balance onto my PayPal account another way?",
            ],
        },
    ],
    "fraud_alert": [
        {
            "opener": "I just got a notification about a $347 charge I didn't make! Someone is using my PayPal business account.",
            "turns": [
                "I was at home all day. The charge is from a store I've never heard of — 'TechMart Online'.",
                "Can you freeze my account right now to prevent more charges?",
                "I see there might be another pending charge for $89.99 too!",
                "Should I change my password? I'm really worried about my business funds.",
                "How long does the investigation take? I can't afford to lose this money.",
            ],
        },
        {
            "opener": "I got an email saying someone logged into my PayPal from Russia. I've never been to Russia.",
            "turns": [
                "The email says the login was from Moscow at 3 AM my time.",
                "I didn't click any links in the email — I went directly to PayPal's website.",
                "I can see in my activity that there was an actual login attempt. This is real.",
                "Did they access any of my financial information?",
                "I want to set up two-factor authentication. Can you help me do that now?",
            ],
        },
        {
            "opener": "I think my card was skimmed at a gas station. Now there are charges I don't recognize on PayPal.",
            "turns": [
                "I filled up gas two days ago at a station on Highway 101. Since then, three weird charges.",
                "The charges are $12.99, $45.00, and $199.99 — all from different merchants.",
                "I've already reported the card to my bank. But these went through PayPal.",
                "Can PayPal dispute these charges on my behalf?",
                "Should I remove this card from PayPal entirely?",
            ],
        },
        {
            "opener": "I received an email saying my account is locked and I need to verify my identity. Is this a phishing scam?",
            "turns": [
                "The email looks official but the sender address is support@paypa1-verify.com.",
                "I almost clicked the link. Good thing I came here first.",
                "Can you confirm my account is NOT actually locked?",
                "How do I report this phishing email to PayPal?",
                "Are there other scams I should watch out for?",
            ],
        },
        {
            "opener": "Someone applied for PayPal Credit in my name. I never applied for any credit product.",
            "turns": [
                "I got a letter saying I was approved for $5,000 in PayPal Credit. I never applied.",
                "This is identity theft. What do I do?",
                "Can you cancel this credit line immediately?",
                "Will this affect my credit score? I need to know what to tell the credit bureaus.",
                "Should I file a police report? My business bank account might also be compromised.",
            ],
        },
        {
            "opener": "There's a recurring charge of $14.99/month from a service I never subscribed to. It's been going on for 4 months.",
            "turns": [
                "The charge shows as 'DGTL-MEDIA-PLUS'. I have no idea what that is.",
                "Four charges of $14.99 each — that's $59.96 I want back.",
                "How did they set up a recurring payment on my account without my permission?",
                "Can you block all future charges from this merchant?",
                "I want to review all my active subscriptions and recurring payments.",
            ],
        },
        {
            "opener": "I want to set up two-factor authentication on my PayPal account. Had a scare recently.",
            "turns": [
                "My neighbor's account got hacked last week and it freaked me out.",
                "I use PayPal for my small bakery business — can't afford to lose access.",
                "Do you support authentication apps or just SMS codes?",
                "What about a security key? I have a YubiKey.",
                "Can I also set up login alerts for any new device?",
            ],
        },
        {
            "opener": "I bought a laptop online for $899 but received a box of rocks. The seller won't respond.",
            "turns": [
                "I paid through PayPal on January 15th. The seller is 'BestDeals-Electronics'.",
                "I have photos of what arrived — literally rocks in a laptop box.",
                "The tracking shows delivered, which technically it was, just not what I ordered.",
                "Can I open a dispute through PayPal? The seller has gone silent.",
                "How long do I have to file this dispute? I want to make sure I don't miss the deadline.",
            ],
        },
        {
            "opener": "My email was in that big data breach last month. Now I'm seeing weird activity on PayPal.",
            "turns": [
                "I got a notification from a breach monitoring service about my email being exposed.",
                "There are two login attempts from IPs I don't recognize in the last 24 hours.",
                "I've already changed my password. What else should I do?",
                "Can you review my recent transactions for anything suspicious?",
                "I want to remove my saved payment methods and re-add them fresh.",
            ],
        },
        {
            "opener": "I see three pending authorization holds on my account that I didn't initiate. What's going on?",
            "turns": [
                "The holds are for $1.00, $49.95, and $150.00. I didn't authorize any of them.",
                "The $1.00 one looks like a test charge. Is someone testing my card?",
                "Can you block these and reverse them before they post?",
                "My card isn't physically stolen — it's still in my wallet.",
                "Could my card number have been stolen from an online store?",
            ],
        },
    ],
    "merchant_dispute": [
        {
            "opener": "A customer filed a chargeback on order #PP-28491 but I have proof of delivery. The tracking shows delivered.",
            "turns": [
                "The order was $189.99 for a ceramic vase set. Shipped via USPS Priority.",
                "Tracking number 9400111899223847561234 shows delivered on January 20th.",
                "The customer says they never received it. Could it have been stolen from their porch?",
                "What evidence do I need to submit to win this dispute?",
                "How long does the chargeback process take? This is affecting my cash flow.",
            ],
        },
        {
            "opener": "I'm getting an unusual number of chargebacks this month. Five in two weeks. Something feels off.",
            "turns": [
                "Normally I get maybe one chargeback every few months. This is way above normal.",
                "Three of them are from customers claiming 'item not as described'. But my products haven't changed.",
                "Could this be a coordinated fraud ring targeting my store?",
                "Am I at risk of PayPal limiting my account because of the chargeback rate?",
                "What's the threshold before PayPal takes action on my account?",
            ],
        },
        {
            "opener": "A customer wants a refund but they bought the item 45 days ago and my policy says 30 days. What are my rights?",
            "turns": [
                "My return policy is clearly stated on my website and in the PayPal listing.",
                "The item was a custom-printed phone case — it can't be resold.",
                "The customer says the print is fading, but I think they've been using it for 6 weeks.",
                "If they open a PayPal dispute, will you side with them despite my 30-day policy?",
                "Can I offer a partial refund as a compromise? Like 50%?",
            ],
        },
        {
            "opener": "My PayPal seller fees seem higher than expected. I'm being charged 3.49% instead of the 2.99% I was quoted.",
            "turns": [
                "I signed up for the standard seller rate of 2.99% + $0.49 per transaction.",
                "When did the rate change? I wasn't notified about any increase.",
                "I process about $15,000 per month. The extra 0.5% adds up significantly.",
                "Are there volume discounts available for sellers my size?",
                "Can I qualify for the charity rate? My shop donates 10% of proceeds.",
            ],
        },
        {
            "opener": "I need help setting up PayPal checkout on my Shopify store. The integration keeps failing.",
            "turns": [
                "I'm using Shopify's PayPal Commerce Platform integration.",
                "When customers click PayPal checkout, they get a blank popup that never loads.",
                "I've tried disconnecting and reconnecting my PayPal business account twice.",
                "Could it be a conflict with my custom theme's JavaScript?",
                "Is there a way to test the checkout without making a real purchase?",
            ],
        },
        {
            "opener": "I shipped a fragile item and it arrived damaged. The customer wants a full refund but the carrier damaged it.",
            "turns": [
                "It was a handmade ceramic bowl, packed with bubble wrap and foam peanuts.",
                "The box was clearly crushed by the carrier — the customer sent me photos.",
                "I have shipping insurance through USPS. Can I file a claim?",
                "In the meantime, do I have to refund the customer out of my pocket?",
                "Can PayPal help mediate between me, the customer, and USPS?",
            ],
        },
        {
            "opener": "A buyer is threatening to leave bad reviews unless I give them a full refund AND let them keep the product.",
            "turns": [
                "They're basically trying to extort me. The product is exactly as described.",
                "They sent me messages saying they'll 'ruin my business' if I don't comply.",
                "Is this something I can report to PayPal? This feels like buyer abuse.",
                "I have screenshots of their threatening messages. Should I save those?",
                "If they open a dispute, will PayPal consider their threatening behavior?",
            ],
        },
        {
            "opener": "My PayPal business account is on a 21-day hold for all incoming payments. This is killing my business.",
            "turns": [
                "I've been selling for 8 months with zero complaints until now.",
                "I have orders to fulfill but can't access the funds to buy materials.",
                "What triggered the hold? I haven't changed anything about my business.",
                "Is there a way to get the hold reduced or removed? I can provide documentation.",
                "Can adding tracking numbers to my orders help release funds faster?",
            ],
        },
        {
            "opener": "I want to set up PayPal invoicing for my consulting business. Do you offer professional invoice templates?",
            "turns": [
                "I bill hourly at $150/hr for web design consulting.",
                "I need to include itemized hours, project descriptions, and payment terms.",
                "Can I set up recurring invoices for retainer clients?",
                "Do your invoices integrate with accounting software like QuickBooks?",
                "Can I customize the invoice with my business logo and branding?",
            ],
        },
        {
            "opener": "I received a payment in GBP but I want to keep it in pounds rather than auto-converting to USD.",
            "turns": [
                "I have UK customers and I'd rather hold GBP to avoid conversion fees.",
                "Can I set up a GBP balance in my PayPal account?",
                "If I keep a GBP balance, can I use it to pay my UK suppliers directly?",
                "What are the fees for holding multiple currency balances?",
                "Can I choose when to convert the GBP to USD, like when the rate is favorable?",
            ],
        },
    ],
    "account_support": [
        {
            "opener": "I just started a small bakery and I want to set up PayPal to accept payments. Where do I even begin?",
            "turns": [
                "I'm selling cupcakes and custom cakes — both online orders and in-person at farmers markets.",
                "Do I need a business account or can I use my personal one?",
                "What information do I need to set up a business account? My bakery is an LLC.",
                "I also want to accept payments in person at the farmers market. Do you have card readers?",
                "What are the fees for in-person vs. online payments?",
            ],
        },
        {
            "opener": "I'm trying to verify my email address but the verification link keeps expiring before I click it.",
            "turns": [
                "I've requested the verification email 4 times now. Each time it expires in like 5 minutes.",
                "The email takes about 10 minutes to arrive. By then the link is dead.",
                "Can you manually verify my email? It's jordan.kim@example.com.",
                "Is there an alternative way to verify — like a code I can enter?",
                "I need this done today because I'm supposed to receive a payment tomorrow.",
            ],
        },
        {
            "opener": "I want to understand the difference between a personal and business PayPal account. Which one should I get?",
            "turns": [
                "I sell handmade jewelry on Etsy, about 10-20 orders per month.",
                "Right now I'm using my personal account. Will PayPal limit me for business use?",
                "Can I upgrade from personal to business without losing my transaction history?",
                "Do business accounts have higher fees than personal?",
                "What about taxes — does PayPal report my income to the IRS?",
            ],
        },
        {
            "opener": "I forgot my password and the phone number on my account is my old number. I can't receive the verification code.",
            "turns": [
                "I changed my phone number 6 months ago and forgot to update PayPal.",
                "I still have access to my email address — can you send the code there instead?",
                "My email is jordan.kim@example.com and I can verify my last 4 transactions.",
                "Once I get back in, can you help me update my phone number?",
                "I also want to set up a backup recovery method. What options are there?",
            ],
        },
        {
            "opener": "I want to set up a PayPal.me link for my tutoring business. How does that work?",
            "turns": [
                "I tutor high school students in math. Most parents want to pay me electronically.",
                "Can I customize my PayPal.me link to something like paypal.me/KimTutoring?",
                "Can I set a default amount on the link? Like $60 for a one-hour session?",
                "Is there a way to track which payments are from which students?",
                "What do parents see on their bank statement when they pay through PayPal.me?",
            ],
        },
        {
            "opener": "I'm a college student and I just turned 18. Can I set up my own PayPal account now?",
            "turns": [
                "I was using my mom's account before but I want my own for my side hustle.",
                "I sell digital art prints online. Is there a student account or special rates?",
                "I don't have a credit card yet — can I link just a debit card?",
                "How do I get the money out of PayPal and into my bank account?",
                "Is there a minimum amount I need to transfer to my bank?",
            ],
        },
        {
            "opener": "I closed my PayPal account last year but now I want to reopen it. Is that possible?",
            "turns": [
                "I closed it because I wasn't using it, but now I need it for a new business.",
                "Can I reopen with the same email address or do I need a new one?",
                "Will my old transaction history still be there?",
                "I had a small balance when I closed — what happened to that money?",
                "Can you help me through the reopening process right now?",
            ],
        },
        {
            "opener": "I want to change my business name on PayPal. I'm rebranding from 'Kim's Cupcakes' to 'Seoul Sweet'.",
            "turns": [
                "I've already updated my LLC with the state. I have the amendment paperwork.",
                "Do I need to create a whole new account or can I update the existing one?",
                "Will changing the name affect my existing transaction history?",
                "I also want to update my logo and business description on PayPal.",
                "After the name change, will my PayPal.me link change too?",
            ],
        },
        {
            "opener": "How do I add my business partner to my PayPal business account? We're co-owners.",
            "turns": [
                "We run a small coffee shop together. We both need to access the funds.",
                "Can we both be admins or does one person have to be the 'owner'?",
                "Can I set different permission levels — like she can view but not withdraw?",
                "We want separate logins but access to the same balance.",
                "What happens if we decide to split the business later?",
            ],
        },
        {
            "opener": "I'm trying to send money to my brother for rent but it says I've exceeded my sending limit.",
            "turns": [
                "The limit says $500 but I need to send $750.",
                "I've had this account for 3 months. Why is there a limit?",
                "What do I need to do to increase my limit? I've already verified my email.",
                "Will linking a bank account help raise the limit?",
                "Can I send $500 today and $250 tomorrow as a workaround?",
            ],
        },
    ],
    "international_transfer": [
        {
            "opener": "Hola, I need to send $2,400 to a client in Mexico but the fees seem really high. Is there a cheaper way to do cross-border transfers?",
            "turns": [
                "I'm a freelance translator based in Miami. I regularly send payments to collaborators in Mexico and Spain.",
                "The fee calculator shows $45 for this transfer. That's almost 2%. Is that the best rate?",
                "What exchange rate are you using? The market rate right now is 17.15 MXN per USD.",
                "My client prefers to receive in pesos. Can I specify the exact MXN amount?",
                "Are there volume discounts if I send more than $5,000 per month internationally?",
            ],
        },
        {
            "opener": "I received a payment from a client in Germany but the amount is less than expected after conversion. What happened?",
            "turns": [
                "They sent EUR 3,000 but I only got $3,089 in my account. The market rate should give me about $3,240.",
                "That's a $151 difference — almost 5%! Is that all PayPal's conversion fee?",
                "Can I hold euros in my PayPal account instead of auto-converting?",
                "I have another EUR payment coming next week. How do I avoid this conversion loss?",
                "Is there a way to set a target exchange rate and convert when it hits that?",
            ],
        },
        {
            "opener": "I'm sending monthly payments to my mother in Colombia. What's the most cost-effective way to do this?",
            "turns": [
                "I send her $500 every month. She uses it for living expenses.",
                "She doesn't have a bank account — she picks up cash at an agent location.",
                "Does PayPal support cash pickup in Colombia? Like at an Efecty or Baloto?",
                "She's not very tech-savvy. What's the simplest way for her to receive the money?",
                "Can I set up automatic monthly transfers so I don't have to remember each time?",
            ],
        },
        {
            "opener": "I need to invoice a client in Japan but I'm not sure how to handle the yen conversion.",
            "turns": [
                "The project fee is JPY 450,000. I want to invoice in yen but receive USD.",
                "When does the conversion happen — when I send the invoice or when they pay?",
                "Can I create the invoice in yen using PayPal's invoicing tool?",
                "The client is asking about PayPal fees on their end. What do they pay?",
                "Are there any restrictions on receiving payments from Japan?",
            ],
        },
        {
            "opener": "My transfer to Spain has been stuck in 'processing' for 5 days. Normally it takes 2. Que pasa?",
            "turns": [
                "I sent EUR 1,800 to my colleague in Barcelona last Tuesday.",
                "They haven't received anything. The status just says 'processing'.",
                "Could it be stuck because of the amount? I usually send smaller amounts.",
                "My colleague needs the money for a conference registration deadline on Friday.",
                "Is there a way to expedite international transfers? I'll pay extra if needed.",
            ],
        },
        {
            "opener": "I want to set up a multi-currency account. I work with clients in USD, EUR, and GBP.",
            "turns": [
                "I'm tired of PayPal auto-converting everything to USD. I lose money each time.",
                "Can I hold balances in all three currencies simultaneously?",
                "When a client pays in EUR, I want to keep it as EUR until I decide to convert.",
                "Is there a fee for maintaining multiple currency balances?",
                "Can I pay EUR vendors directly from my EUR balance?",
            ],
        },
        {
            "opener": "I've been charged a 'cross-border fee' on a payment from a US client. But I'm also in the US — I'm in Miami.",
            "turns": [
                "The client is in New York. We're both in the US. Why the cross-border fee?",
                "Could it be because my account was originally created in Argentina before I moved?",
                "I've been a US resident for 5 years. How do I update my account country?",
                "Will I lose my transaction history if I change my account country?",
                "Necesito that this gets fixed — it's costing me money on every domestic transaction.",
            ],
        },
        {
            "opener": "I'm worried about reporting requirements for international transfers. Do I need to file anything with the IRS?",
            "turns": [
                "I receive about $40,000 per year from international clients in total.",
                "Does PayPal send a 1099 for international payments?",
                "What about FBAR reporting? Do PayPal balances count as foreign accounts?",
                "My accountant is asking about the source countries. Can I get a breakdown?",
                "Is there a report I can download showing all my international transactions by country?",
            ],
        },
        {
            "opener": "My recipient in Brazil says they were charged a high fee to receive my payment. Is that normal?",
            "turns": [
                "I sent $1,000 and they received about $940 in Brazilian reais equivalent.",
                "That's 6% gone in fees. Who's charging what — PayPal or the Brazilian banks?",
                "Is there a way to pay all fees on my end so my recipient gets the full amount?",
                "Would it be cheaper if I sent the money in BRL instead of USD?",
                "Are there alternative PayPal products better suited for regular Brazil transfers?",
            ],
        },
        {
            "opener": "I need to send payments to 15 different translators across 8 countries this month. Is there a batch payment option?",
            "turns": [
                "The amounts range from $200 to $3,000 per person. Total is about $18,000.",
                "They're in Mexico, Spain, Argentina, Germany, France, Japan, UK, and Brazil.",
                "Doing 15 individual transfers is tedious and the fees add up. Is there a mass pay option?",
                "Can I upload a CSV file with all the recipients and amounts?",
                "What's the fee structure for mass payments? Is it cheaper per transaction?",
            ],
        },
    ],
    "api_integration": [
        {
            "opener": "Getting 401 on POST /v2/checkout/orders in sandbox. Bearer token from /v1/oauth2/token looks valid. Headers: Content-Type application/json, Authorization Bearer {token}. What am I missing?",
            "turns": [
                "Token response has 'scope' field but it's just 'openid'. Do I need specific scopes for orders?",
                "My client ID is from a sandbox REST app. Do I need to request additional permissions?",
                "Switching to client_credentials grant. Previously was using authorization_code.",
                "OK, 401 resolved. Now getting 422 on the order body. Here's my JSON payload.",
                "Fixed the schema. Orders API is working. Next: how do I capture the payment after buyer approves?",
            ],
        },
        {
            "opener": "Need to set up webhooks for order.completed events. What's the endpoint format and how do I verify the signature?",
            "turns": [
                "I'm running a Node.js backend on Express. HTTPS with Let's Encrypt cert.",
                "The webhook URL will be https://api.myapp.com/webhooks/paypal. What headers do you send?",
                "For signature verification — do I use the webhook ID or the cert URL from the header?",
                "Getting the webhook events in sandbox but verification always returns false. Using crypto.verify with SHA256.",
                "Figured it out — was using wrong algorithm. Should be SHA256withRSA. Webhooks verified now.",
            ],
        },
        {
            "opener": "IPN vs webhooks — which should I use for a new SaaS integration? IPN docs seem outdated.",
            "turns": [
                "My SaaS handles subscriptions. Need real-time notification when payments succeed or fail.",
                "So webhooks are the recommended path. Can I listen for both subscription and one-time payment events?",
                "What happens if my server is down when a webhook fires? Is there retry logic?",
                "How many retry attempts and what's the backoff schedule?",
                "Can I manually resend a missed webhook event from the dashboard for testing?",
            ],
        },
        {
            "opener": "Implementing PayPal subscriptions API. Getting RESOURCE_NOT_FOUND when creating a subscription with a plan_id.",
            "turns": [
                "Plan was created in sandbox. ID: P-2AB12345CD678901E. Status shows ACTIVE.",
                "Using POST /v1/billing/subscriptions with plan_id in the body.",
                "Wait — am I supposed to use the plan_id or the product_id?",
                "Got it. Plan ID is correct but I was using the wrong sandbox URL prefix. Fixed.",
                "Subscription created. How do I handle the approval redirect? SPA with React.",
            ],
        },
        {
            "opener": "Need to implement refunds via API. What's the endpoint and can I do partial refunds?",
            "turns": [
                "I have capture IDs from completed payments. Want to allow partial refunds from my admin panel.",
                "POST /v2/payments/captures/{id}/refund — is the amount field optional for full refund?",
                "What currency format? {value: '10.00', currency_code: 'USD'}?",
                "Is there a time limit on how long after capture I can issue a refund?",
                "Can I issue multiple partial refunds on the same capture up to the original amount?",
            ],
        },
        {
            "opener": "PayPal JS SDK is loading slowly in production. 3-4 seconds to render the buttons. Any optimization tips?",
            "turns": [
                "Currently loading the SDK in the main HTML head. It blocks page render.",
                "Tried async/defer but then the buttons container errors because SDK isn't ready.",
                "Is there a way to lazy-load the SDK only when the user reaches the checkout page?",
                "What about the data-sdk-integration-source attribute? Does that affect loading?",
                "Can I preconnect to PayPal domains to reduce DNS/TLS overhead?",
            ],
        },
        {
            "opener": "Testing in sandbox. How do I simulate different payment scenarios — declined cards, pending payments, etc.?",
            "turns": [
                "I need to test: successful payment, declined card, pending review, and buyer cancellation.",
                "Are there specific sandbox credit card numbers for different decline codes?",
                "How do I simulate a pending payment that later completes?",
                "Can I create multiple sandbox buyer accounts with different scenarios?",
                "Is there a way to trigger webhook events manually in sandbox without making actual API calls?",
            ],
        },
        {
            "opener": "Migrating from PayPal Classic API (NVP) to REST v2. What's the mapping for DoExpressCheckoutPayment?",
            "turns": [
                "We've been on Classic for 6 years. Management finally approved the migration.",
                "DoExpressCheckoutPayment -> POST /v2/checkout/orders/{id}/capture — is that right?",
                "What about SetExpressCheckout? Is it just POST /v2/checkout/orders?",
                "Our current integration uses reference transactions. What's the REST equivalent?",
                "Is there a migration guide or tool that can help automate the conversion?",
            ],
        },
        {
            "opener": "How do I implement idempotency in PayPal API calls? Getting duplicate charges in production.",
            "turns": [
                "A customer clicked 'pay' twice quickly and got charged twice.",
                "I see there's a PayPal-Request-Id header. Is that the idempotency key?",
                "What format should the idempotency key be? UUID? Or can it be my order ID?",
                "If I send the same request with the same idempotency key, does PayPal return the original response?",
                "What's the TTL on idempotency keys? How long does PayPal cache them?",
            ],
        },
        {
            "opener": "Need to implement 3DS authentication for European customers. SCA compliance for PSD2.",
            "turns": [
                "We have European customers so we need to comply with Strong Customer Authentication.",
                "Does PayPal handle 3DS automatically or do I need to integrate it explicitly?",
                "When using the Orders API, is SCA enforced by default for EU transactions?",
                "What happens if 3DS fails — does the payment decline or fall back to non-3DS?",
                "Any specific API flags I need to set for SCA-eligible transactions?",
            ],
        },
    ],
}

# ---------------------------------------------------------------------------
# Orchestrator HTTP helpers
# ---------------------------------------------------------------------------


async def create_session(
    client: httpx.AsyncClient, scenario_id: str
) -> str | None:
    """Create a new session via the orchestrator, return session_id."""
    try:
        resp = await client.post(
            f"{ORCHESTRATOR_URL}/api/sessions",
            json={"scenario_id": scenario_id},
        )
        resp.raise_for_status()
        return resp.json()["session_id"]
    except Exception as exc:
        logger.error("Failed to create session for %s: %s", scenario_id, exc)
        return None


async def send_chat(
    client: httpx.AsyncClient,
    session_id: str,
    scenario_id: str,
    message: str,
) -> dict | None:
    """Send a chat message via the orchestrator, return response dict."""
    try:
        resp = await client.post(
            f"{ORCHESTRATOR_URL}/api/chat",
            json={
                "session_id": session_id,
                "user_message": message,
                "scenario_id": scenario_id,
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error("Chat failed (session %s): %s", session_id, exc)
        return None


async def post_session_end(
    client: httpx.AsyncClient,
    session_id: str,
    agent_id: str,
) -> bool:
    """Post a system.session_end event directly to the Context Graph API."""
    event = {
        "event_id": str(uuid.uuid4()),
        "event_type": "system.session_end",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "agent_id": agent_id,
        "trace_id": str(uuid.uuid4()),
        "payload_ref": "inline:system.session_end",
        "payload": {"reason": "session_completed"},
    }
    try:
        resp = await client.post(f"{CG_API_URL}/v1/events", json=event, timeout=30.0)
        resp.raise_for_status()
        return True
    except Exception as exc:
        logger.warning("Failed to post session_end for %s: %s", session_id, exc)
        return False


# ---------------------------------------------------------------------------
# Persona name mapping
# ---------------------------------------------------------------------------

SCENARIO_PERSONA: dict[str, str] = {
    "billing_dispute": "Sarah Chen",
    "payment_failure": "Alex Rivera",
    "fraud_alert": "Michael Torres",
    "merchant_dispute": "Priya Patel",
    "account_support": "Jordan Kim",
    "international_transfer": "Rosa Martinez",
    "api_integration": "David Park",
}

# ---------------------------------------------------------------------------
# Simulation runner
# ---------------------------------------------------------------------------


async def run_simulation(
    max_sessions: int = 10,
    max_turns: int = 8,
    personas: list[str] | None = None,
) -> dict:
    """Run the full simulation across all personas.

    Returns summary statistics.
    """
    scenario_ids = personas or list(PERSONA_SCRIPTS.keys())
    stats = {
        "total_sessions": 0,
        "total_turns": 0,
        "total_events": 0,
        "errors": 0,
        "per_persona": {},
    }

    async with httpx.AsyncClient(timeout=90.0) as client:
        # Check orchestrator health
        try:
            health = await client.get(f"{ORCHESTRATOR_URL}/api/health")
            health.raise_for_status()
            logger.info("Orchestrator is healthy")
        except Exception:
            logger.error(
                "Orchestrator not reachable at %s. Is it running?",
                ORCHESTRATOR_URL,
            )
            return stats

        for scenario_id in scenario_ids:
            scripts = PERSONA_SCRIPTS[scenario_id]
            persona_name = SCENARIO_PERSONA[scenario_id]
            sessions_to_run = min(max_sessions, len(scripts))
            persona_stats = {"sessions": 0, "turns": 0, "events": 0, "errors": 0}

            logger.info(
                "=== %s (%s) — %d sessions ===",
                persona_name,
                scenario_id,
                sessions_to_run,
            )

            for session_idx in range(sessions_to_run):
                script = scripts[session_idx]
                session_id = await create_session(client, scenario_id)
                if not session_id:
                    persona_stats["errors"] += 1
                    continue

                # Determine number of turns for this session
                available_turns = 1 + len(script["turns"])  # opener + follow-ups
                turns_this_session = min(max_turns, available_turns)

                logger.info(
                    "  [%d/%d] Session %s — %d turns",
                    session_idx + 1,
                    sessions_to_run,
                    session_id,
                    turns_this_session,
                )

                # Send opener
                result = await send_chat(
                    client, session_id, scenario_id, script["opener"]
                )
                if result:
                    context_used = result.get("context_used", 0)
                    persona_stats["turns"] += 1
                    persona_stats["events"] += 2
                    logger.info(
                        "    Turn 1/%d — context: %d nodes",
                        turns_this_session,
                        context_used,
                    )
                else:
                    persona_stats["errors"] += 1

                # Send follow-ups
                for turn_idx, turn_msg in enumerate(
                    script["turns"][: turns_this_session - 1], start=2
                ):
                    # Small delay between turns to avoid overwhelming the API
                    await asyncio.sleep(0.3)
                    result = await send_chat(
                        client, session_id, scenario_id, turn_msg
                    )
                    if result:
                        context_used = result.get("context_used", 0)
                        persona_stats["turns"] += 1
                        persona_stats["events"] += 2
                        logger.info(
                            "    Turn %d/%d — context: %d nodes",
                            turn_idx,
                            turns_this_session,
                            context_used,
                        )
                    else:
                        persona_stats["errors"] += 1

                # Post session_end event to trigger extraction
                await post_session_end(client, session_id, persona_name)
                persona_stats["sessions"] += 1

                # Brief delay between sessions for workers to process
                await asyncio.sleep(1.5)

            stats["per_persona"][scenario_id] = persona_stats
            stats["total_sessions"] += persona_stats["sessions"]
            stats["total_turns"] += persona_stats["turns"]
            stats["total_events"] += persona_stats["events"]
            stats["errors"] += persona_stats["errors"]

            logger.info(
                "  Done: %d sessions, %d turns, %d events, %d errors",
                persona_stats["sessions"],
                persona_stats["turns"],
                persona_stats["events"],
                persona_stats["errors"],
            )

    return stats


# ---------------------------------------------------------------------------
# Graph analysis
# ---------------------------------------------------------------------------


async def analyze_graph() -> None:
    """Run analysis queries against Neo4j and Redis, print results."""
    from neo4j import AsyncGraphDatabase

    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
    neo4j_password = os.environ.get("NEO4J_PASSWORD", "engram-dev-password")

    driver = AsyncGraphDatabase.driver(
        neo4j_uri, auth=(neo4j_user, neo4j_password)
    )

    queries = [
        (
            "Node counts by label",
            "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC",
        ),
        (
            "Edge counts by type",
            "MATCH ()-[r]->() RETURN type(r) AS rel_type, count(r) AS count ORDER BY count DESC",
        ),
        (
            "Top 20 entities by connections",
            "MATCH (e:Entity)-[r]-() RETURN e.name AS name, e.entity_type AS type, count(r) AS connections ORDER BY connections DESC LIMIT 20",
        ),
        (
            "Preferences by category",
            "MATCH (p:Preference) RETURN p.category AS category, p.polarity AS polarity, count(p) AS count ORDER BY count DESC",
        ),
        (
            "Top skills by proficiency",
            "MATCH (s:Skill) RETURN s.category AS category, s.name AS name, s.proficiency AS proficiency ORDER BY s.proficiency DESC LIMIT 20",
        ),
        (
            "User profiles",
            "MATCH (u:UserProfile) RETURN u.name AS name, u.tech_level AS tech_level, u.total_sessions AS total_sessions ORDER BY u.total_sessions DESC",
        ),
        (
            "Cross-session entity overlap",
            """
            MATCH (ev:Event)-[:REFERENCES]->(e:Entity)
            WITH e, collect(DISTINCT ev.session_id) AS sessions
            WHERE size(sessions) > 1
            RETURN e.name AS name, e.entity_type AS type, size(sessions) AS session_count
            ORDER BY session_count DESC LIMIT 15
            """,
        ),
        (
            "Total graph statistics",
            """
            MATCH (n) WITH count(n) AS total_nodes
            OPTIONAL MATCH ()-[r]->() WITH total_nodes, count(r) AS total_edges
            RETURN total_nodes, total_edges
            """,
        ),
    ]

    print("\n" + "=" * 70)
    print("GRAPH ANALYSIS RESULTS")
    print("=" * 70)

    async with driver.session() as session:
        for title, query in queries:
            print(f"\n--- {title} ---")
            try:
                result = await session.run(query)
                records = await result.data()
                if not records:
                    print("  (no data)")
                    continue
                # Print header
                keys = list(records[0].keys())
                header = "  " + " | ".join(f"{k:>20}" for k in keys)
                print(header)
                print("  " + "-" * len(header.strip()))
                for row in records:
                    values = " | ".join(f"{str(row[k]):>20}" for k in keys)
                    print(f"  {values}")
            except Exception as exc:
                print(f"  ERROR: {exc}")

    await driver.close()

    # Redis stats
    print(f"\n--- Redis event count ---")
    try:
        import redis.asyncio as aioredis

        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        redis_client = aioredis.from_url(redis_url, decode_responses=True)
        # Count event keys
        cursor, keys = await redis_client.scan(cursor=0, match="evt:*", count=1000)
        event_count = len(keys)
        while cursor != 0:
            cursor, batch = await redis_client.scan(
                cursor=cursor, match="evt:*", count=1000
            )
            event_count += len(batch)
        print(f"  Total event keys (evt:*): {event_count}")

        # Stream info
        try:
            stream_info = await redis_client.xinfo_stream("events")
            print(f"  Stream 'events' length: {stream_info.get('length', 'N/A')}")
        except Exception:
            print("  Stream 'events': not found or error")

        await redis_client.aclose()
    except Exception as exc:
        print(f"  Redis stats unavailable: {exc}")

    print("\n" + "=" * 70)


# ---------------------------------------------------------------------------
# Context-aware return session demo
# ---------------------------------------------------------------------------


async def context_demo() -> None:
    """Run a returning-customer session to show context enrichment."""
    print("\n" + "=" * 70)
    print("CONTEXT-AWARE RETURN SESSION DEMO")
    print("=" * 70)

    scenario_id = "billing_dispute"
    persona_name = "Sarah Chen"

    async with httpx.AsyncClient(timeout=90.0) as client:
        # Check health
        try:
            health = await client.get(f"{ORCHESTRATOR_URL}/api/health")
            health.raise_for_status()
        except Exception:
            print("ERROR: Orchestrator not reachable")
            return

        # Create session
        session_id = await create_session(client, scenario_id)
        if not session_id:
            print("ERROR: Failed to create session")
            return

        print(f"\nSession: {session_id}")
        print(f"Persona: {persona_name} (returning customer)")
        print(f"Scenario: {scenario_id}")

        # A new topic that a returning customer might raise
        conversation = [
            "Hi, it's Sarah Chen again. I was looking at my billing history and noticed something — can you check if my team's subscription was affected by last month's duplicate charge issue?",
            "Also, I'd like to explore upgrading to the Enterprise plan for our team. We've grown from 5 to 12 engineers.",
            "What would the per-seat pricing look like for Enterprise? And does it include priority support?",
            "Given my history with billing issues, is there any loyalty discount you can offer?",
            "One more thing — I set up that billing manager role for my colleague earlier. Can you confirm she has the right access level?",
        ]

        print(f"\n--- Conversation ({len(conversation)} turns) ---\n")

        for turn_idx, user_msg in enumerate(conversation, start=1):
            print(f"[User Turn {turn_idx}]")
            print(f"  {user_msg[:120]}{'...' if len(user_msg) > 120 else ''}")

            result = await send_chat(client, session_id, scenario_id, user_msg)
            if result:
                context_nodes = result.get("context_used", 0)
                intents = result.get("inferred_intents", {})
                agent_msg = result.get("agent_message", "")

                print(f"  Context nodes used: {context_nodes}")
                if intents:
                    top_intents = sorted(
                        intents.items(), key=lambda x: x[1], reverse=True
                    )[:3]
                    intent_str = ", ".join(
                        f"{k}={v:.2f}" for k, v in top_intents
                    )
                    print(f"  Inferred intents: {intent_str}")
                print(f"[Agent]")
                # Truncate long responses for readability
                if len(agent_msg) > 300:
                    print(f"  {agent_msg[:300]}...")
                else:
                    print(f"  {agent_msg}")
                print()
            else:
                print("  ERROR: Chat failed\n")

            await asyncio.sleep(0.5)

        # Post session_end
        await post_session_end(client, session_id, persona_name)
        print(f"\nSession ended. session_end event posted for extraction.")

        # Also query context directly to show what's available
        print(f"\n--- Direct Context Graph Query ---")
        try:
            resp = await client.get(
                f"{CG_API_URL}/v1/context/{session_id}",
                params={"query": "Sarah Chen billing history", "max_nodes": 50},
                timeout=30.0,
            )
            resp.raise_for_status()
            atlas = resp.json()
            nodes = atlas.get("nodes", {})
            edges = atlas.get("edges", [])
            meta = atlas.get("meta", {})

            print(f"  Total context nodes: {len(nodes)}")
            print(f"  Total context edges: {len(edges)}")
            print(f"  Query time: {meta.get('query_ms', 'N/A')} ms")

            # Group nodes by type
            node_types: dict[str, int] = {}
            for node in nodes.values():
                nt = node.get("node_type", "Unknown")
                node_types[nt] = node_types.get(nt, 0) + 1

            if node_types:
                print("  Nodes by type:")
                for nt, count in sorted(
                    node_types.items(), key=lambda x: x[1], reverse=True
                ):
                    print(f"    {nt}: {count}")
        except Exception as exc:
            print(f"  Context query failed: {exc}")

    print("\n" + "=" * 70)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="PayPal Persona Simulation for Engram Context Graph"
    )
    parser.add_argument(
        "--sessions",
        type=int,
        default=10,
        help="Max sessions per persona (default: 10)",
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=8,
        help="Max turns per session (default: 8)",
    )
    parser.add_argument(
        "--personas",
        nargs="*",
        help="Specific persona scenario IDs to run (default: all 7)",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Run graph analysis only (skip simulation)",
    )
    parser.add_argument(
        "--context-demo",
        action="store_true",
        help="Run context-aware return session demo only",
    )
    args = parser.parse_args()

    if args.analyze:
        asyncio.run(analyze_graph())
        return

    if args.context_demo:
        asyncio.run(context_demo())
        return

    # Full simulation
    start = time.time()
    logger.info(
        "Starting simulation: sessions=%d, turns=%d, personas=%s",
        args.sessions,
        args.turns,
        args.personas or "all",
    )

    stats = asyncio.run(
        run_simulation(
            max_sessions=args.sessions,
            max_turns=args.turns,
            personas=args.personas,
        )
    )

    elapsed = time.time() - start
    print("\n" + "=" * 70)
    print("SIMULATION COMPLETE")
    print("=" * 70)
    print(f"  Duration:        {elapsed:.1f}s")
    print(f"  Total sessions:  {stats['total_sessions']}")
    print(f"  Total turns:     {stats['total_turns']}")
    print(f"  Total events:    {stats['total_events']}")
    print(f"  Errors:          {stats['errors']}")
    print()
    for scenario_id, ps in stats.get("per_persona", {}).items():
        persona = SCENARIO_PERSONA.get(scenario_id, scenario_id)
        print(
            f"  {persona:25s}  sessions={ps['sessions']}  turns={ps['turns']}  "
            f"events={ps['events']}  errors={ps['errors']}"
        )
    print("=" * 70)

    # Suggest next steps
    print("\nNext steps:")
    print("  1. Wait ~30s for extraction workers to process session_end events")
    print("  2. Run analysis:     python -m demo.orchestrator.simulate --analyze")
    print("  3. Run context demo: python -m demo.orchestrator.simulate --context-demo")


if __name__ == "__main__":
    main()
