import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
import matplotlib.pyplot as plt  
from tqdm import tqdm

def fetch_articles(api_key, query, from_date, to_date, page_size=200):
    base_url = "https://content.guardianapis.com/search"
    articles = []
    current_page = 1
    total_pages = 1  # Initialized with 1 to ensure the loop starts
    
    print(f"Fetching articles for {query} from {from_date} to {to_date}...")
    
    while current_page <= total_pages:
        params = {
            'api-key': api_key,
            'q': query,
            'from-date': from_date,
            'to-date': to_date,
            'page': current_page,
            'page-size': page_size,
            'order-by': "newest"
        }
        
        response = requests.get(base_url, params=params)
        data = response.json()
        
        if data['response']['status'] == 'ok':
            articles.extend(data['response']['results'])
            if current_page % 10 == 0 or current_page == 1 or current_page == total_pages:
                print(f"Processed page {current_page} of {data['response']['pages']}.")
            current_page += 1
            total_pages = data['response']['pages']
        else:
            print("Error fetching the data: ", data['response']['status'])
            break

    print(f"Finished fetching articles. Total articles fetched: {len(articles)}")
    return articles

def process_new_articles(new_articles):
    articles_count = defaultdict(int)
    section_names = defaultdict(set)

    for article in new_articles:
        date_str = article['webPublicationDate'].split('T')[0]  # extract the date
        date = pd.to_datetime(date_str).strftime("%Y-%m-%d")  # format the date
        section = article['sectionName']
        articles_count[(date, section)] += 1
        section_names[date].add(section)
        
    data_for_df = []

    for (date, section), count in articles_count.items():
        data_for_df.append({
            'Date': date,
            'Number of Articles': count,
            'SectionName': section
        })

    # Create df
    df = pd.DataFrame(data_for_df)

    # sort by date and then SectionName
    df.sort_values(by=['Date', 'SectionName'], inplace=True)
    return df


    
def update_data_and_plot(api_key, query, csv_file_path,root_path):
    # Load existing data and find the last date
    try:
        df_existing = pd.read_csv(csv_file_path, parse_dates=['Date'])
        last_date = df_existing['Date'].max().strftime("%Y-%m-%d")
        print(f"Got existing df with last date {last_date}")
    except (FileNotFoundError, pd.errors.EmptyDataError):
        df_existing = pd.DataFrame(columns=['Date', 'Number of Articles', 'SectionName'])
        last_date = pd.Timestamp('2018-01-01').strftime('%Y-%m-%d')  # Start from 2018 if no file exists
#         last_date = pd.Timestamp('2023-06-01').strftime('%Y-%m-%d') # For Test
        print("Created Fresh dataframe")

    # Fetch articles from the day after the last date in the CSV to today
    from_date = (pd.to_datetime(last_date) + timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"from date: {from_date}")
    to_date = datetime.now().strftime('%Y-%m-%d')
    print(f"to date: {to_date}")
    new_articles = fetch_articles(api_key, query, from_date, to_date)
    print("fetched new articles")

    # Check if new articles were fetched
    if new_articles:
        df = process_new_articles(new_articles)

        # Append the new data to the existing data
        df_updated = pd.concat([df_existing, df], ignore_index=True, sort=False)
        df_updated.drop_duplicates(subset=['Date', 'SectionName'], keep='last', inplace=True)
        df_updated.sort_values(by=['Date', 'SectionName'], inplace=True)
        df_updated.to_csv(csv_file_path, index=False)
        print("New csv saved!")
        
        # Plot
        daily_count = df_updated.groupby('Date')['Number of Articles'].sum()
        df = pd.DataFrame(daily_count).reset_index()
        
        # Convert 'Date' column to datetime format
        df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m-%d')
        
        # Extract earliest and latest years from the DataFrame
        earliest_year = df['Date'].dt.year.min()
        latest_year = df['Date'].dt.year.max()

        # Plot
        plt.figure(figsize=(14, 7))
        plt.plot(df['Date'], df['Number of Articles'], label='Number of Articles', color='royalblue')

        plt.title('Evolution of Number of Articles Over Time')
        plt.xlabel('Year')
        plt.ylabel('Number of Articles')
        plt.legend()
        plt.grid(False)

        monthly_ticks = pd.date_range(start=f'{earliest_year}-01-01', end=f'{latest_year}-12-31', freq='MS')
        plt.xticks(monthly_ticks, [date.strftime('%Y') for date in monthly_ticks], rotation=90)

        for n, label in enumerate(plt.gca().xaxis.get_ticklabels()):
            if n % 12 != 0:
                label.set_visible(False)
        # Save plot
        plt.savefig(os.path.join(root_path,'articles_trend.png'), dpi=300)
        plt.close()
        print("Plot Saved!")
        
        return True

    else:
        print("No new articles to update.")
        return False


# Function to send email with attached plot to multiple recipients
def send_email(sender_email, sender_password, recipient_emails, subject, body, attachment_path):
    for recipient_email in recipient_emails:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject

        # Attach body
        msg.attach(MIMEText(body, 'plain'))

        # Attach plot
        with open(attachment_path, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename= {os.path.basename(attachment_path)}')
        msg.attach(part)

        # Connect to SMTP server and send email
        server = smtplib.SMTP('smtp-mail.outlook.com', 587)  # Update with your SMTP server details (Googled my hotmail SMTP server)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()

# Main function to update data and plot daily
def main():
    root_path = '/Users/nitinnandansingh/Documents/TheGuardianTask_HolidayCheck/'
    
    # Set API key and file path
    api_key = 'API-KEY'
    query = "Justin Trudeau"
    csv_file_path = os.path.join(root_path,'articles.csv')
    
    
    print("Starting the script...")
    
    # Update data and plot
    success = update_data_and_plot(api_key, query, csv_file_path, root_path)
    
    
    if success:
        # Send email with plot
        sender_email = 'nitinnandansingh@hotmail.com'
        sender_password = 'PASSWORD'
        subject = 'Daily Article Plot'
        body = 'Please find attached the daily plot of articles from The Guardian.'
        attachment_path = os.path.join(root_path,'articles_trend.png')

        # Usage
        recipient_emails = ['nnsmostwanted@gmail.com','nishak996@gmail.com'] 
        
        send_email(sender_email, sender_password, recipient_emails, subject, body, attachment_path)
        print("email sent!")
        print("---------------------------------")
    else:
        print("email not sent")
        print("---------------------------------")

if __name__ == "__main__":
    main()