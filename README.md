# Guardian Article Analysis and Email Notification System

## Overview
This Python script fetches articles from The Guardian's API, processes the data, generates plots, and sends daily email notifications with the latest article trends to specified recipients.

## Functionality
1. **Fetching Articles**
   - The script fetches articles from The Guardian's API based on a specified query, date range, and API key.

2. **Processing Data**
   - The fetched articles are processed to count the number of articles published each day within different sections.
   - The data is structured into a pandas DataFrame for analysis.

3. **Updating Data and Plotting**
   - Existing data is loaded from a CSV file (if it exists) to track trends.
   - New articles are fetched since the last recorded date, and the data is updated.
   - Monthly totals of the number of articles are calculated and plotted over time.
   - Plots are saved as PNG files for attachment in the email.

4. **Sending Email Notifications**
   - The script sends daily email notifications with the latest article trends.
   - The email includes a subject, body, and attached plot.

## Example Usage
```bash
python guardian_article_analysis.py
