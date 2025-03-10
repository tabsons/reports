# http://10.18.50.26:5000/api/tabsons/getreport/1010022/14-01-2023

import os
from flask import Flask, render_template, request, send_file, redirect, session, Blueprint
from datetime import datetime, timedelta
import pandas as pd
import requests
import re
import pytz
import ren
import time as time


eq_route = Blueprint('eq_route', __name__)

@eq_route.route('/eq_reports', methods=['GET', 'POST'])
def Reports():
    if 'username' not in session:
        return redirect('/login')
    return render_template('index_eq.html')

@eq_route.route('/eq_results', methods=['GET', 'POST'])
def Results():
    dir = os.getcwd()
    newDir = os.path.join(dir,'counts')
    if os.path.exists(newDir):
        pass
    else:
        os.mkdir(newDir)

    dt = datetime.now()
    date = str(dt.date())
    file = os.path.join(newDir, f"{date}.txt")

    if os.path.exists(file):
        with open(file, 'r') as efile:
            counts = efile.readline()
            newCount = int(counts) + 1
        with open(file, 'w') as efile:
            efile.write(f'{newCount}')
    else:
        with open(file, 'w') as efile:
            efile.write('1')
    start_date = request.args.get('start_date')
    start_time = request.args.get('start_time')
    end_date = request.args.get('end_date')
    end_time = request.args.get('end_time')
    channel_ids = request.args.get('channel_ids').split(",")
    filler_time = request.args.get('filler_time')
    
    
    try:
        
        all = []
        current_date = f'{start_date[-2:]}-{start_date[5:7]}-{start_date[:4]}'
        end_dated = f'{end_date[-2:]}-{end_date[5:7]}-{end_date[:4]}'
        delta = timedelta(days=1)
        while datetime.strptime(current_date, '%d-%m-%Y') <= datetime.strptime(end_dated, '%d-%m-%Y'):
            print(f'http://10.18.50.26:5000/api/tabsons/getreport/{channel_ids[0]}/{current_date}')
            current_data_api = f'http://10.18.50.26:5000/api/tabsons/getreport/{channel_ids[0]}/{current_date}'
            response = requests.get(current_data_api)
            if response.status_code == 200:
                try:
                    json_data = response.json()['TabsonsReport']
                    if len(json_data) != 0:
                        df = pd.DataFrame(json_data)
                
                        df = df.sort_values(['ClipStartTime'])
                    
                        df.index = range(1, len(df)+1)
                    
                        df = df.drop('SNO', axis=1).reset_index(names='SNO')
                        mask = (df['ClipStartTime'] >= start_time) & (df['ClipEndTime'] <= end_time) & (df['ClipEndTime'] >= '05:30:00')
                        print(len(df))
                        df = df[mask]
                        
                    
                        all.append(df)

                    CurrentPlusOne = datetime.strptime(current_date, '%d-%m-%Y') + timedelta(days=1)
                    current_date = CurrentPlusOne.strftime('%d-%m-%Y')
                    
                    
                except Exception as e:
                    # return f"An error occurred while processing the response data: {str(e)}"
                    return f"No Data Available!"
            else:
                return f"Request failed with status code: {response.status_code}"
        df = pd.concat(all, ignore_index=True)
        duplicate_lines = df.duplicated(subset=['ClipStartDate', 'ClipStartTime']).sum()
        first_line = df.iloc[[0]]
        report_start_time = first_line['ClipStartTime'][df.index[0]]
        df_length = len(df) - 1
        end_line = df.iloc[[-1]]
        report_end_time = end_line['ClipEndTime'][df_length]

        
        if 'ProgramType' in df.columns:
            df = df.sort_values('ProgramType')
            value_counts = df['TelecastFormat'].value_counts()
            story_block_count = value_counts.get('Shows', 0)
            filler_count = value_counts.get('', 0)
                            # Count headlines and fast news import requests
            if 'TelecastFormat' in df.columns:
                df = df.sort_values('TelecastFormat')
                fastnews_count = df['TelecastFormat'].value_counts().get('FastNews', 0)
                headline_count = df['TelecastFormat'].value_counts().get('Headlines', 0)
                expressnews_count = df['TelecastFormat'].value_counts().get('Express News', 0)
                expressheadlines_count = df['TelecastFormat'].value_counts().get('Express Headlines', 0)
            
            else:
                headline_count = 0
        else:
            return "Required columns are missing in the DataFrame."    

            

        # df.reset_index(drop=True, inplace=True)
        df = df.sort_values(['ClipStartDate','SNO'])

        filler_df = df[df['ProgramType'] != 'News']
        filler_df['duration'] = filler_df['ClipDuration'].apply(lambda x: timedelta(hours= int(x[:2]), minutes = int(x[3:5]), seconds= int(x[-2:])))

        news = (df['TelecastFormat'] == 'News').sum()
        check_df = df[(df['TelecastFormat'] == 'Shows') | (df['TelecastFormat'] == 'Headlines') | (df['TelecastFormat'] == 'FastNews') | (df['TelecastFormat'] == 'Express Headlines') | (df['TelecastFormat'] == 'Express News')]
        check_df['duration'] = check_df['ClipDuration'].apply(lambda x: timedelta(hours= int(x[:2]), minutes = int(x[3:5]), seconds= int(x[-2:])))
        stories_duration = check_df['duration'].sum()
        fillers_duration = filler_df['duration'].sum()
        total_duration = stories_duration + fillers_duration
        stories_duration = format_timedelta(stories_duration)
        fillers_duration = format_timedelta(fillers_duration)
        total_duration = format_timedelta(total_duration)
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
        
        big_fillers = (df[df['Description']=='Filler']['ClipDuration'] > filler_time).sum()
        ind = df[(df['Description'] == 'Filler') & (df['ClipDuration'] > filler_time)]
        print(len(df), len(ind))
        big_fillers_df = ind[['channelname','Description', 'ClipStartDate', 'ClipEndDate', 'ClipStartTime', 'ClipEndTime', 'ClipDuration', 'VideoURL']]

        blank_stories_df = pd.concat([no_story_df, null_stories_df])
        blank_stories_df = blank_stories_df[['SNO', 'channelname', 'Description','ClipStartDate', 'ClipStartTime', 'ClipEndDate', 'ClipEndTime', 'ClipDuration', 'VideoURL']]
        
        

        # Generate Excel file
        output_filename = f"report{start_date}.xlsx"
        df.to_excel(output_filename, index=False)

        # Calculate the final story block count
        # story_block_count= story_block_count - headline_count

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
                            blank_stories_df=blank_stories_df.to_html())
                                                
                        
                
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
