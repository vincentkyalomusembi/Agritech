# Africa's Talking USSD Setup

## Step 1: Create Account
1. Go to https://account.africastalking.com/auth/register
2. Sign up for a free sandbox account
3. Verify your email and phone number

## Step 2: Get API Credentials
1. Login to your dashboard
2. Go to Settings → API Keys
3. Copy your API Key and Username

## Step 3: Create USSD Channel
1. Go to USSD → Channels
2. Click "Create Channel"
3. Fill in:
   - Channel Name: Agritech AI
   - USSD Code: *384*1234# (or available code)
   - Callback URL: https://your-ngrok-url.ngrok-free.app/ussd

## Step 4: Test Numbers
Sandbox test numbers: +254711XXXYYY, +254733XXXYYY