def human_format(num, no_decimals=False, percentage=False):
    if percentage:
        return f"{num:.2%}"

    # Check if the number is zero
    if num == 0:
        return "0"
    if num < 100 and no_decimals:
        return f"{num:.0f}"

    # Define the magnitude labels for numbers greater than or equal to 1
    magnitude_labels = ["", "K", "M", "B", "T"]
    magnitude = 0

    # Handle numbers smaller than 1 by returning exactly 3 significant digits
    if abs(num) < 1:
        return f"{num:.3g}"

    # Determine the magnitude for numbers greater than or equal to 1
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0

    # Format the number to ensure 3 digits
    if num >= 100:
        # If the number is 100 or greater, no decimal places are needed
        formatted_num = f"{num:.0f}"
    elif num >= 10:
        # If the number is between 10 and 99.9, one decimal place is needed
        formatted_num = f"{num:.1f}"
    else:
        # If the number is less than 10, two decimal places are needed
        formatted_num = f"{num:.2f}"

    # Return the formatted number with the appropriate suffix
    return f"{formatted_num}{magnitude_labels[magnitude]}"
