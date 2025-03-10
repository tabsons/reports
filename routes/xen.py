from flask import Flask, render_template, request, send_file, redirect, session, Blueprint
from datetime import datetime, timedelta
import os
import pandas as pd
import requests
import re
import pytz
import ren
import time as time

xen_route = Blueprint('xen_route', __name__)

@xen_route.route('/reports', methods=['GET', 'POST'])
def Reports():
    if 'username' not in session:
        return redirect('/login')
    return render_template('index.html')


@xen_route.route('/results', methods=['GET', 'POST'])
def Results():
    dir = os.getcwd()
    print(dir)
    newDir = os.path.join(dir,'counts')
    print(newDir)
    if os.path.exists(newDir):
        pass
    else:
        os.mkdir(newDir)

    dt = datetime.now()
    print(dt)
    date = str(dt.date())
    print(date)
    file = os.path.join(newDir, f"{date}.txt")
    print(file)

    if os.path.exists(file):
        with open(file, 'r') as efile:
            counts = efile.readline()
            print('counts', counts)
            newCount = int(counts) + 1
        print('new count',newCount)
        with open(file, 'w') as efile:
            efile.write(f'{newCount}')
    else:
        with open(file, 'w') as efile:
            efile.write('1')

    api_endpoints = {
        'API 1': 'http://10.18.80.14:2996/command/ExportEPGTabsons',
        'API 2': 'http://10.18.80.15:2996/command/ExportEPGTabsons'
    }
    selected_api = request.args.get('api')
    start_date = request.args.get('start_date')
    start_time = request.args.get('start_time')
    end_date = request.args.get('end_date')
    end_time = request.args.get('end_time')
    channel_ids = request.args.get('channel_ids').split(",")
    filler_time = request.args.get('filler_time')
    print('fillertime', filler_time)

    # Convert start_time and end_time to datetime objects
    start_datetime = datetime.strptime(start_date + " " + start_time, "%Y-%m-%d %H:%M:%S")
    end_datetime = datetime.strptime(end_date + " " + end_time, "%Y-%m-%d %H:%M:%S")

    # Convert start_datetime and end_datetime to UTC
    start_datetime_utc = start_datetime.astimezone(pytz.utc)
    end_datetime_utc = end_datetime.astimezone(pytz.utc)
    print(start_date, end_date)
    payload = {
        "StartDateUTC": start_datetime_utc.strftime("%Y-%m-%dT%H:%M:%S"),
        "EndDateUTC": end_datetime_utc.strftime("%Y-%m-%dT%H:%M:%S"),
        "SignalIds": [],
        "ChannelIds": channel_ids
    }

    try:
        api_url = api_endpoints[selected_api]
        response = requests.post(api_url, json=payload)

        if response.status_code == 200:
            try:
                json_data = response.json()
                df = pd.DataFrame(json_data)
                duplicate_lines = df.duplicated(subset=['ClipStartDate', 'ClipStartTime']).sum()
                if 'ProgramType' in df.columns:
                    first_line = df.iloc[[0]]
                    report_start_time = first_line['ClipStartTime'][df.index[0]]
                    print('start time report ', report_start_time)
                    df_length = len(df) - 1

                    end_line = df.iloc[[-1]]
                    report_end_time = end_line['ClipEndTime'][df_length]
                    print('end time', report_end_time)
                    value_counts = df['ProgramType'].value_counts()
                    story_block_count = value_counts.get('Story Block', 0)
                    filler_count = value_counts.get('Filler', 0)
                    

                    # Count headlines and fast news import requests
                    if 'TelecastFormat' in df.columns:
                        df = df.sort_values('TelecastFormat')
                        headline_count = df['TelecastFormat'].value_counts().get('HEADLINES', 0)
                        fastnews_count = df['TelecastFormat'].value_counts().get('FASTNEWS', 0)
                        expressnews_count = df['TelecastFormat'].value_counts().get('Express News', 0)
                        expressheadlines_count = df['TelecastFormat'].value_counts().get('Express Headlines', 0)
                        
                    else:
                        headline_count = 0

                    df.reset_index(drop=True, inplace=True)
                    df = df.sort_values('SNO')
                
                    filler_df = df[df['ProgramType'] == 'Filler']
                    filler_df['duration'] = filler_df['ClipDuration'].apply(lambda x: timedelta(hours= int(x[:2]), minutes = int(x[3:5]), seconds= int(x[-2:])))
                    check_df = df[(df['TelecastFormat'] == 'SHOWS') | (df['TelecastFormat'] == 'HEADLINES') | (df['TelecastFormat'] == 'FASTNEWS') | (df['TelecastFormat'] == 'Express News') | (df['TelecastFormat'] == 'Express Headlines')]
                    check_df['duration'] = check_df['ClipDuration'].apply(lambda x: timedelta(hours= int(x[:2]), minutes = int(x[3:5]), seconds= int(x[-2:])))
                    stories_duration = check_df[check_df['ProgramType'] == 'Story Block']['duration'].sum()
                    fillers_duration = filler_df[filler_df['ProgramType'] == 'Filler']['duration'].sum()
                    total_duration = stories_duration + fillers_duration
                    stories_duration = format_timedelta(stories_duration)
                    fillers_duration = format_timedelta(fillers_duration)
                    total_duration = format_timedelta(total_duration)
                    print('durations', stories_duration, fillers_duration)
                    null_stories = check_df['Description'].isnull().sum()
                    null_stories_df = check_df[check_df['Description'].isnull()]
                    no_story = (check_df['Description'].str.strip() == '').sum()
                    no_story_df = check_df[check_df['Description'].str.strip() == '']
                    no_substory = (check_df['SubStory'].str.strip() == '').sum()
                    null_substory = check_df['SubStory'].isnull().sum()
                    no_StoryGenre = (check_df['StoryGenre'].str.strip() == '').sum()
                    null_StoryGenre = check_df['StoryGenre'].isnull().sum()
                    no_Geography = (check_df['Geography'].str.strip() == '').sum()
                    null_Geography = check_df['Geography'].isnull().sum()
                    blank_stories_df = pd.concat([no_story_df, null_stories_df])
                    blank_stories_df = blank_stories_df[['SNO', 'channelname', 'Description','ClipStartDate', 'ClipStartTime', 'ClipEndDate', 'ClipEndTime', 'ClipDuration', 'VideoURL']]
                    
                    big_fillers = (df[df['ProgramType']=='Filler']['ClipDuration'] > filler_time).sum()
                    ind = df[(df['ProgramType'] == 'Filler') & (df['ClipDuration'] > filler_time)]
                    big_fillers_df = ind[['channelname','ProgramType', 'ClipStartDate', 'ClipEndDate', 'ClipStartTime', 'ClipEndTime', 'ClipDuration', 'VideoURL']]

                    # Generate Excel file
                    output_filename = f"report{start_date}.xlsx"
                    df.to_excel(output_filename, index=False)

                    # Calculate the final story block count
                    story_block_count= story_block_count - headline_count - fastnews_count - expressnews_count - expressheadlines_count

                    return render_template('result.html', story_block_count=story_block_count,
                                            filler_count=filler_count, dataframe=df.to_html(),
                                            output_filename=output_filename,
                                            headline_count=headline_count + fastnews_count + expressnews_count + expressheadlines_count, null_stories = null_stories+ no_story, big_fillers= big_fillers,
                            null_substory= null_substory+no_substory,
                            null_StoryGenre = null_StoryGenre+ no_StoryGenre,
                            null_Geography= null_Geography+ no_Geography,
                            stories_duration = stories_duration,
                            fillers_duration = fillers_duration,
                            total_duration = total_duration,
                            report_start_time= report_start_time,
                            report_end_time= report_end_time,
                            duplicate_lines = duplicate_lines,
                            big_fillers_df=big_fillers_df.to_html(),
                            blank_stories_df= blank_stories_df.to_html())
                                            
                else:
                    return "No Data Available!"
            except Exception as e:
                # return f"An error occurred while processing the response data: {str(e)}"
                return f"No Data Available!"
        else:
            return f"Request failed with status code: {response.status_code}"
    except Exception as e:
        # return f"An error occurred while making the API request: {str(e)}"
        return f"Check Your Internet Connection!"
    


def format_timedelta(duration):
    hours = duration.days * 24 + duration.seconds // 3600
    minutes = (duration.seconds % 3600) // 60
    seconds = duration.seconds % 60

    # Format the timedelta object to 'HH:MM:SS'
    formatted_duration = "{:02}:{:02}:{:02}".format(hours, minutes, seconds)
    return formatted_duration