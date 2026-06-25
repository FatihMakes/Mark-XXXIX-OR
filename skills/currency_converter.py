import requests

MANIFEST = {
    "name": "currency_converter",
    "description": "Converts an amount from one currency to another using current exchange rates.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "amount": {
                "type": "number",
                "description": "The amount of money to convert.",
                "example": 100.50
            },
            "from_currency": {
                "type": "string",
                "description": "The 3-letter ISO code of the currency to convert from (e.g., 'USD', 'EUR', 'GBP').",
                "example": "USD"
            },
            "to_currency": {
                "type": "string",
                "description": "The 3-letter ISO code of the currency to convert to (e.g., 'JPY', 'CAD', 'AUD').",
                "example": "EUR"
            }
        },
        "required": ["amount", "from_currency", "to_currency"]
    }
}

def run(parameters=None, player=None, speak=None) -> str:
    if not parameters:
        return "I need an amount, a source currency, and a target currency to perform a conversion."

    amount = parameters.get("amount")
    from_currency = parameters.get("from_currency")
    to_currency = parameters.get("to_currency")

    if not all([amount, from_currency, to_currency]):
        return "Missing one or more required parameters: amount, from_currency, or to_currency."

    try:
        amount = float(amount)
        if amount <= 0:
            return "The amount to convert must be a positive number."
    except (ValueError, TypeError):
        return f"Invalid amount provided: '{amount}'. It must be a number."

    if not isinstance(from_currency, str) or not isinstance(to_currency, str):
        return "Currency codes must be strings."

    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if len(from_currency) != 3 or len(to_currency) != 3:
        return "Please provide 3-letter ISO currency codes (e.g., USD, EUR)."

    if from_currency == to_currency:
        return f"{amount:.2f} {from_currency} is, of course, {amount:.2f} {to_currency}."

    api_url = f"https://api.frankfurter.app/latest?amount={amount}&from={from_currency}&to={to_currency}"

    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        data = response.json()

        if "error" in data:
            return f"Error from currency API: {data['error']}"

        if not data.get("rates") or to_currency not in data["rates"]:
            return f"Could not find exchange rate for {from_currency} to {to_currency}. Please check the currency codes."

        converted_amount = data["rates"][to_currency]
        return f"{amount:.2f} {from_currency} is approximately {converted_amount:.2f} {to_currency}."

    except requests.exceptions.Timeout:
        return "The currency conversion service took too long to respond. Please try again later."
    except requests.exceptions.ConnectionError:
        return "I am unable to connect to the currency conversion service. Please check your network connection."
    except requests.exceptions.HTTPError as http_err:
        if http_err.response.status_code == 400:
            try:
                error_data = http_err.response.json()
                if "error" in error_data:
                    return f"Currency conversion failed: {error_data['error']}"
            except ValueError:
                pass # Fallback to generic HTTP error
        return f"Currency conversion service returned an error: {http_err}. Status code: {http_err.response.status_code}"
    except ValueError:
        return "Failed to parse the response from the currency conversion service."
    except Exception as e:
        return f"An unexpected error occurred during currency conversion: {e}"