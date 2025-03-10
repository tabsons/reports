import os
from flask import Flask, render_template, request, send_file, redirect, session, Blueprint
import pandas as pd
from datetime import datetime
import re

story_routes = Blueprint('story_routes', __name__)

@story_routes.route('/getduplicates', methods=['GET', 'POST'])
def story():
    print('story duplicates')
    if request.method == 'POST':
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
        file = request.files['file']
        ratio = float(f'0.{request.form["Ratio"][0]}')

        ex = pd.ExcelFile(file)
        sheets = ex.sheet_names
        df = pd.DataFrame()
        if 'story standardization' in sheets:
            print(1)
            xl = pd.read_excel(file, sheet_name='story standardization')
            df['Story'] = xl['Suggested Headline']
        else:
            print(2)
            xl = pd.read_excel(file, sheet_name='expressreport')
            df['Story'] = xl['Story']
            ab = 'story'

        df = df.drop_duplicates()
        df = df.astype(str, copy=False)
        df = df.sort_values('Story')

        def replacewords(statement, dic=['-', '/', '-', '_', '&', '*', '$', '#', '%', '@']):
            for n in dic:
                statement = statement.replace(n, '')
            return statement

        def replacewords2(statement):
            dic = ['-', '/', '-', '_', '&', '*', '$', '#', '%', '@']
            for n in dic:
                statement = re.sub(n, '', statement)
            return statement

        def jaccard_similarity(x, y):
            intersection_cardinality = len(set.intersection(*[set(x), set(y)]))
            union_cardinality = len(set.union(*[set(x), set(y)]))
            res = intersection_cardinality / float(union_cardinality)
            return res

        def word_similarity(x, y):
            x = set(x.split())
            y = set(y.split())
            z = len(x.intersection(y))
            w = len(x.union(y))
            res = z / w
            return res

        out = pd.DataFrame(columns=['story1', 'story2', 'result', 'w_story1', 'w_story2'])
        stories_done = ''
        print('starting on story')
        for i in df['Story'].str.strip():
            for ii in df['Story'].str.strip():
                if i != ii:
                    score = word_similarity(replacewords(i), replacewords(ii))
                    if score >= ratio and i not in stories_done:
                        row = {
                            'story1': i,
                            'story2': ii,
                            'result': score,
                            'w_story1': replacewords(i),
                            'w_story2': replacewords(ii)
                        }
                        out = pd.concat([out, pd.DataFrame([row])], ignore_index=True)
                        stories_done += ii

        excel_file = 'output.xlsx'
        print('sending file')
        out.to_excel(excel_file, sheet_name='Sheet1', index=False)
        return send_file(excel_file, as_attachment=True)
    else:
        return render_template('story.html')
    #return "Service is unvailable for now"