import requests
import pandas as pd
import numpy as np
from difflib import SequenceMatcher
from flask import render_template, request, redirect, session, Blueprint, send_file

celebs_route = Blueprint('celebs_route', __name__)

@celebs_route.route('/celeb/',methods=['GET', 'POST'])
def celebs():
    if request.method == 'POST':
        file = request.files['file']
        df = pd.read_excel(file, sheet_name = "expressreport")
        celeb_type = request.form['celeb']
        if celeb_type == "Personality":
            df_split = df.assign(Personality = df[celeb_type].str.split(';')).explode(celeb_type)
        elif celeb_type == "Guest":
            df_split = df.assign(Guest = df[celeb_type].str.split(';')).explode(celeb_type)
        elif celeb_type == "Anchor":
            df_split = df.assign(Anchor = df[celeb_type].str.split(';')).explode(celeb_type)
        elif celeb_type == "Reporter":
            df_split = df.assign(Reporter = df[celeb_type].str.split(';')).explode(celeb_type)
        pivot = df_split.reset_index(drop=True)
        pivot = pivot.groupby([celeb_type, 'Channel Name']).size().unstack(fill_value=0)
        dic = {}
        for i in range(len(pivot)):
            if '(' in pivot.index[i]:
                cele = pivot.index[i].split("(")[0]
            else:
                cele = pivot.index[i]
            dic[(cele).strip()] = list(pivot.iloc[i][pivot.iloc[i] != 0].index)
        
        
        
        celeb_type = request.form['celeb']

        d1 = df[celeb_type].fillna('')
        celebrities = []
        for i in d1:
            if i != "":
                if ';' in i:
                    a = i.split(';')
                    for j in a:
                        celebrities.append(j)
                else:
                    celebrities.append(i)
        
        all = pd.DataFrame()
        all[celeb_type] = celebrities
        all = all.drop_duplicates()
        excel_file = 'output.xlsx'
        #all.to_excel(excel_file, sheet_name='Sheet1', index=False)

        df = all
        df = df.astype('str',copy=False)

        # delimitting
        l1 = []
        l2 = []
        for i in df[df.columns[0]]:
            if "(" in i:
                j  = i.split("(")
                a,b = j[0],j[1]
                l1.append(a.strip())
                l2.append(b.replace(")","").strip())
            else:
                l1.append(i.strip())
                l2.append(np.nan)

        df = pd.DataFrame()
        df[celeb_type] = l1
        df['Channel or Org'] = l2


        from gensim.models import FastText
        model = FastText(vector_size= 500,  window= 5, min_count=1)

        # Configuring Names for model training 
        # removing left right whitespaces
        li = []
        for i in df[df.columns[0]]:
            lis = []
            lis.append(i)
            li.append(lis)
        print('Total Stories : ', len(li))

        # training model on data
        model.build_vocab(corpus_iterable = li)
        model.train(corpus_iterable=li,total_examples=len(li), epochs=1)

        ## Defining Required functions

        import string 
        duos = []
        for i in string.ascii_uppercase: duos.append(2*i)
            
        def remove_repetition(st):
                for i in duos:
                    if i in st:
                        st = st.replace(i,i[0])
                return st

        def remove_vowels(word):
            vowels = ['A','E','I','O','U']
            wrd = ''
            for i in word:
                if i not in vowels:
                    wrd += i
            return wrd

        def remove_duplicates(df):
            df = df.reset_index(drop= True)
            concat = []
            for index in range(len(df)):
                concat.append(f'{df["Original"][index]} {df["Duplicates"][index]}')
            df_concat = pd.DataFrame(concat)
            dup = df_concat[df_concat.duplicated()]
            dup_indexes = dup.index.values
            df.drop(dup_indexes,axis = 0,inplace = True)
            return df

        def remove_cross_duplicates(df):
            df = df.reset_index(drop= True)
            concat1 = []
            for index in range(len(df)):
                concat1.append(f'{df["Original"][index]} {df["Duplicates"][index]}')
            concat2 = []
            for index in range(len(df)):
                concat2.append(f'{df["Duplicates"][index]} {df["Original"][index]}')
            o = []
            num = 0
            for a,b in enumerate(concat1):
                for i,j in enumerate(concat2):
                    if b == j and a not in o:
                        o.append(i)
            df.drop(o,axis = 0, inplace = True)
            return df

        ## Finding  & Collecting mOst similar Value
        ori = []
        lis = []
        for name in li:
            sim = model.wv.most_similar(remove_repetition(name[0]),topn=5)
            for value,_ in sim:
                ori.append(name[0])
                lis.append(value)

        matches = []
        for index in range(len(ori)):
            n = ori[index]
            m = lis[index]
            matches.append(SequenceMatcher(None,n,m).ratio())

        df2 = pd.DataFrame()
        df2['Original'] = ori
        df2['Duplicates'] = lis
        df2['Ratio'] = matches

        # Removing Totally Unnecessary Data
        df3 = df2[df2['Ratio']>= 0.6]
        df3 = remove_duplicates(df3)
        df3 = remove_cross_duplicates(df3)
        df3 = df3.reset_index(drop = True)

        n_sim = []  # collecting matches by removing vowels
        n_sim3 = [] # collecting matches by removing vowels + splitting values
        for index in range(len(df3)):
            n = remove_vowels(df3["Original"][index])
            m = remove_vowels(df3["Duplicates"][index])
            n_sim.append(model.wv.n_similarity(n,m))
            n_sim3.append(model.wv.n_similarity(n.split(),m.split()))

        n_sim2 = [] # collecting values without filtering
        for index in range(len(df3)):
            m = df3["Original"][index]
            n = df3["Duplicates"][index]
            n_sim2.append(model.wv.n_similarity(m,n))

        # bringing together
        df3['n_sim'] = n_sim
        df3['n_sim2'] = n_sim2
        df3["n_sim3"] = n_sim3

        ## OPERATION 2 ON 2

        df3 = df3.reset_index(drop=True)
        dubls = []
        for i in range(len(df3)):
            if len(df3['Original'][i].split())== 2 and len(df3["Duplicates"][i].split())== 2:
                dubls.append(i)
        doubles = df3.iloc[dubls]

        doubles = doubles.reset_index(drop=True)
        outd = []
        for i in range(len(doubles)):
            if len(doubles['Original'][i].split()[0])<=2 or len(doubles["Duplicates"][i].split()[0])<= 2:
                if doubles['Original'][i].split()[0][0] == doubles["Duplicates"][i].split()[0][0]:
                    outd.append(i)
        shorts = doubles.iloc[outd]
        len(shorts)

        d_ups = doubles[doubles['Ratio']>= 0.88]

        d_downs = doubles[doubles['Ratio']<0.88]
        d_downs1 = d_downs[d_downs['n_sim']>=0.93]
        d_downs2 = d_downs[d_downs['n_sim2']>=0.93]
        d_downs3 = d_downs[d_downs['n_sim3']>=0.90]

        d_frame = [d_downs1,d_downs2,d_downs3]
        d_downss = pd.concat(d_frame)
        d_downss = remove_duplicates(d_downss)
        d_downss = remove_cross_duplicates(d_downss)

        l = []
        l.extend(list(d_downs1.index))
        l.extend(list(d_downs2.index))
        l.extend(list(d_downs3.index))
        l = set(l)

        downs = d_downs.drop(l,axis = 0)
        downs = downs[downs['n_sim2']>=0.88]
        downs = downs.reset_index(drop = True)
        len(downs)

        ## Operation - 3 on all

        tri_li = []
        for i in range(len(df3)):
            if len(df3['Original'][i].split()) >= 3 or len(df3['Duplicates'][i].split()) >= 3:
                tri_li.append(i)
        triples = df3.iloc[tri_li]
        triples = triples
        triples_up = triples[triples["Ratio"] >= 0.88]
        triples_down = triples[triples["Ratio"] < 0.88]
        triples_down1 = triples_down[triples_down['n_sim']>= 0.90]
        triples_down2 = triples_down[triples_down['n_sim2']>= 0.87]
        triples_down3 = triples_down[triples_down['n_sim3']>= 0.90]


        tri_frames = [triples_up, triples_down1, triples_down2 ,triples_down3]
        tripless = pd.concat(tri_frames)
        tripless = remove_duplicates(tripless)
        tripless = remove_cross_duplicates(tripless)
        len(tripless)
        #tripless.to_excel('triples.xlsx')

        ## OPerations 1 on 1
        if celeb_type == "Anchor" or celeb_type == "Reporter":

            s_on_s = []
            for i in li:
                if len(i[0].split()) == 1:
                    s_on_s.append(i)
            model1 = FastText(vector_size= 300,  window= 5, min_count=1)
            model1.build_vocab(corpus_iterable = s_on_s)
            model1.train(corpus_iterable=s_on_s,total_examples=len(s_on_s), epochs=1)

            ori1 = []
            lis1 = []
            for name in s_on_s:
                sim = model1.wv.most_similar(remove_repetition(name[0]),topn=3)
                for value,_ in sim:
                    ori1.append(name[0])
                    lis1.append(value)
                    
            matches1 = []
            for index in range(len(ori1)):
                n = ori1[index]
                m = lis1[index]
                matches1.append(SequenceMatcher(None,n,m).ratio())
                
            df1 = pd.DataFrame()
            df1['Original'] = ori1
            df1["Duplicates"] = lis1
            df1['Ratio'] = matches1
            df1 = df1[df1['Ratio']>= 0.8]
            df1 = remove_duplicates(df1)
            df1 = remove_cross_duplicates(df1)
            #df1.to_excel('one_on_one.xlsx')
            len(df1)

            split_list = []
            for i in li:
                split_list.append(i[0].split())
                
                
            chk1 = []
            chk2 = []
            for value in li:
                for text in split_list:
                    if len(value[0].split()) == 1 and value[0] in text:
                        chk1.append(value[0])
                        chk2.append(' '.join(text))
            df_single = pd.DataFrame(chk1,chk2).reset_index()
            df_single.columns = ['Original','Duplicates']
            o = []
            for i in range(len(df_single)):
                if df_single[df_single.columns[0]][i] == df_single[df_single.columns[1]][i]:
                    o.append(i)
                
            df_single.drop(o,axis = 0, inplace = True)
            df_single.columns = ['Duplicates', "Original"]



            frames = [d_ups,d_downss,shorts,tripless,df1,df_single]
        else:
            frames = [d_ups,d_downss,shorts,tripless]

        df_final = pd.concat(frames)
        df_final = remove_duplicates(df_final)
        df_final = remove_cross_duplicates(df_final)


        df.columns = [celeb_type,'Channel or Org']
        Org = []
        for value in df['Channel or Org']:
            Org.append(value)
        df['Org'] = Org

        Origi = []
        for value in df[celeb_type]:
            Origi.append(value.strip())
        df[celeb_type] = Origi



        df4 = pd.DataFrame()
        df4[celeb_type] = df[df.columns[0]]
        df4['Channel or Org'] = df[df.columns[1]]
        #df.columns = [celeb_type,'Channel or Org']
        #df.drop(['Org'],axis = 1 , inplace = True)

        """
        Org = []
        for value in df4['Channel or Org']:
            Org.append(value)
        df4['Channel or Org'] = Org
        """

        Origi = []
        for value in df4[celeb_type]:
            Origi.append(value.strip())
        df4[celeb_type] = Origi

        df_final = pd.merge(df_final,df4,left_on = "Original", right_on = celeb_type, how= "inner")
        df_final = pd.merge(df_final,df4,left_on = "Duplicates", right_on = celeb_type ,how= "inner")
        


        
        df2 = pd.DataFrame()

        df2['Original'] = df_final['Original']

        df2['Duplicates'] = df_final['Duplicates']

        l1 = []
        l2 = []
        same = []

        for i in range(len(df_final)):
            l1 = dic[df2['Original'][i]]
            l2 = dic[df2['Duplicates'][i]]
            n = False
            for m in l1:
                if m in l2 and n == False:
                    n = True
            same.append(n)
        df_final['Same Channel'] = same
        df_final.to_excel(excel_file, sheet_name='Sheet1', index=False)
        df_final.drop(['n_sim','n_sim3','Ratio',f'{celeb_type}_x',f'{celeb_type}_y'],inplace=True,axis = 1)


        return send_file(excel_file, as_attachment=True)
    return render_template('celebs.html')


@celebs_route.route('/celebs/',methods=['GET', 'POST'])
def celebs_master():
        if request.method == 'POST':
            file = request.files['file']
            data = pd.read_excel(file)   
            df = pd.DataFrame()
            celeb_type = data['Type'][0]
            df = df.astype('str',copy=False)
            master = pd.read_excel(f'{celeb_type}.xlsx')
            master_df = master[['Person Name','Status', 'Total Count' ]]


            df[celeb_type] = data['Person Name']
            df[celeb_type] =df[celeb_type].fillna('')
            df['Channel Name'] = data['Channel Name']


            from gensim.models import FastText
            model = FastText(vector_size= 500,  window= 5, min_count=1)

            # Configuring Names for model training 
            # removing left right whitespaces
            li = []
            for i in df[df.columns[0]]:
                lis = []
                lis.append(i)
                li.append(lis)
            print('Total Stories : ', len(li))

            # training model on data
            model.build_vocab(corpus_iterable = li)
            model.train(corpus_iterable=li,total_examples=len(li), epochs=1)

            ## Defining Required functions

            import string 
            duos = []
            for i in string.ascii_uppercase: duos.append(2*i)
                
            def remove_repetition(st):
                    for i in duos:
                        if i in st:
                            st = st.replace(i,i[0])
                    return st

            def remove_vowels(word):
                vowels = ['A','E','I','O','U']
                wrd = ''
                for i in word:
                    if i not in vowels:
                        wrd += i
                return wrd

            def remove_duplicates(df):
                df = df.reset_index(drop= True)
                concat = []
                for index in range(len(df)):
                    concat.append(f'{df["Original"][index]} {df["Duplicates"][index]}')
                df_concat = pd.DataFrame(concat)
                dup = df_concat[df_concat.duplicated()]
                dup_indexes = dup.index.values
                df.drop(dup_indexes,axis = 0,inplace = True)
                return df

            def remove_cross_duplicates(df):
                df = df.reset_index(drop= True)
                concat1 = []
                for index in range(len(df)):
                    concat1.append(f'{df["Original"][index]} {df["Duplicates"][index]}')
                concat2 = []
                for index in range(len(df)):
                    concat2.append(f'{df["Duplicates"][index]} {df["Original"][index]}')
                o = []
                num = 0
                for a,b in enumerate(concat1):
                    for i,j in enumerate(concat2):
                        if b == j and a not in o:
                            o.append(i)
                df.drop(o,axis = 0, inplace = True)
                return df

            ## Finding  & Collecting mOst similar Value
            ori = []
            lis = []
            for name in li:
                print(name[0])
                sim = model.wv.most_similar(remove_repetition(name[0]),topn=5)
                for value,_ in sim:
                    ori.append(name[0])
                    lis.append(value)

            matches = []
            for index in range(len(ori)):
                n = ori[index]
                m = lis[index]
                matches.append(SequenceMatcher(None,n,m).ratio())

            df2 = pd.DataFrame()
            df2['Original'] = ori
            df2['Duplicates'] = lis
            df2['Ratio'] = matches

            # Removing Totally Unnecessary Data
            df3 = df2[df2['Ratio']>= 0.6]
            df3 = remove_duplicates(df3)
            df3 = remove_cross_duplicates(df3)
            df3 = df3.reset_index(drop = True)

            n_sim = []  # collecting matches by removing vowels
            n_sim3 = [] # collecting matches by removing vowels + splitting values
            for index in range(len(df3)):
                n = remove_vowels(df3["Original"][index])
                m = remove_vowels(df3["Duplicates"][index])
                n_sim.append(model.wv.n_similarity(n,m))
                n_sim3.append(model.wv.n_similarity(n.split(),m.split()))

            n_sim2 = [] # collecting values without filtering
            for index in range(len(df3)):
                m = df3["Original"][index]
                n = df3["Duplicates"][index]
                n_sim2.append(model.wv.n_similarity(m,n))

            # bringing together
            df3['n_sim'] = n_sim
            df3['n_sim2'] = n_sim2
            df3["n_sim3"] = n_sim3

            ## OPERATION 2 ON 2

            df3 = df3.reset_index(drop=True)
            dubls = []
            for i in range(len(df3)):
                if len(df3['Original'][i].split())== 2 and len(df3["Duplicates"][i].split())== 2:
                    dubls.append(i)
            doubles = df3.iloc[dubls]

            doubles = doubles.reset_index(drop=True)
            outd = []
            for i in range(len(doubles)):
                if len(doubles['Original'][i].split()[0])<=2 or len(doubles["Duplicates"][i].split()[0])<= 2:
                    if doubles['Original'][i].split()[0][0] == doubles["Duplicates"][i].split()[0][0]:
                        outd.append(i)
            shorts = doubles.iloc[outd]
            len(shorts)

            d_ups = doubles[doubles['Ratio']>= 0.88]

            d_downs = doubles[doubles['Ratio']<0.88]
            d_downs1 = d_downs[d_downs['n_sim']>=0.93]
            d_downs2 = d_downs[d_downs['n_sim2']>=0.93]
            d_downs3 = d_downs[d_downs['n_sim3']>=0.90]

            d_frame = [d_downs1,d_downs2,d_downs3]
            d_downss = pd.concat(d_frame)
            d_downss = remove_duplicates(d_downss)
            d_downss = remove_cross_duplicates(d_downss)

            l = []
            l.extend(list(d_downs1.index))
            l.extend(list(d_downs2.index))
            l.extend(list(d_downs3.index))
            l = set(l)

            downs = d_downs.drop(l,axis = 0)
            downs = downs[downs['n_sim2']>=0.88]
            downs = downs.reset_index(drop = True)
            len(downs)

            ## Operation - 3 on all

            tri_li = []
            for i in range(len(df3)):
                if len(df3['Original'][i].split()) >= 3 or len(df3['Duplicates'][i].split()) >= 3:
                    tri_li.append(i)
            triples = df3.iloc[tri_li]
            triples = triples
            triples_up = triples[triples["Ratio"] >= 0.88]
            triples_down = triples[triples["Ratio"] < 0.88]
            triples_down1 = triples_down[triples_down['n_sim']>= 0.90]
            triples_down2 = triples_down[triples_down['n_sim2']>= 0.87]
            triples_down3 = triples_down[triples_down['n_sim3']>= 0.90]


            tri_frames = [triples_up, triples_down1, triples_down2 ,triples_down3]
            tripless = pd.concat(tri_frames)
            tripless = remove_duplicates(tripless)
            tripless = remove_cross_duplicates(tripless)
            len(tripless)
            #tripless.to_excel('triples.xlsx')

            ## OPerations 1 on 1
            if celeb_type == "Anchor" or celeb_type == "Reporter":

                s_on_s = []
                for i in li:
                    if len(i[0].split()) == 1:
                        s_on_s.append(i)
                model1 = FastText(vector_size= 300,  window= 5, min_count=1)
                model1.build_vocab(corpus_iterable = s_on_s)
                model1.train(corpus_iterable=s_on_s,total_examples=len(s_on_s), epochs=1)

                ori1 = []
                lis1 = []
                for name in s_on_s:
                    sim = model1.wv.most_similar(remove_repetition(name[0]),topn=3)
                    for value,_ in sim:
                        ori1.append(name[0])
                        lis1.append(value)
                        
                matches1 = []
                for index in range(len(ori1)):
                    n = ori1[index]
                    m = lis1[index]
                    matches1.append(SequenceMatcher(None,n,m).ratio())
                    
                df1 = pd.DataFrame()
                df1['Original'] = ori1
                df1["Duplicates"] = lis1
                df1['Ratio'] = matches1
                df1 = df1[df1['Ratio']>= 0.8]
                df1 = remove_duplicates(df1)
                df1 = remove_cross_duplicates(df1)
                #df1.to_excel('one_on_one.xlsx')
                len(df1)

                split_list = []
                for i in li:
                    split_list.append(i[0].split())
                    
                    
                chk1 = []
                chk2 = []
                for value in li:
                    for text in split_list:
                        if len(value[0].split()) == 1 and value[0] in text:
                            chk1.append(value[0])
                            chk2.append(' '.join(text))
                df_single = pd.DataFrame(chk1,chk2).reset_index()
                df_single.columns = ['Original','Duplicates']
                o = []
                for i in range(len(df_single)):
                    if df_single[df_single.columns[0]][i] == df_single[df_single.columns[1]][i]:
                        o.append(i)
                    
                df_single.drop(o,axis = 0, inplace = True)
                df_single.columns = ['Duplicates', "Original"]



                frames = [d_ups,d_downss,shorts,tripless,df1,df_single]
            else:
                frames = [d_ups,d_downss,shorts,tripless]

            df_final = pd.concat(frames)
            df_final = remove_duplicates(df_final)
            df_final = remove_cross_duplicates(df_final)

            print(df_final)

            df.columns = [celeb_type,'Channel Name']
            Org = []
            for value in df['Channel Name']:
                Org.append(value)
            df['Org'] = Org

            Origi = []
            for value in df[celeb_type]:
                Origi.append(value.strip())
            df[celeb_type] = Origi



            df4 = pd.DataFrame()
            df4[celeb_type] = df[df.columns[0]]
            df4['Channel Name'] = df[df.columns[1]]
            #df.columns = [celeb_type,'Channel or Org']
            #df.drop(['Org'],axis = 1 , inplace = True)

            """
            Org = []
            for value in df4['Channel or Org']:
                Org.append(value)
            df4['Channel or Org'] = Org
            """

            Origi = []
            for value in df4[celeb_type]:
                Origi.append(value.strip())
            df4[celeb_type] = Origi

            df_final = pd.merge(df_final,df4,left_on = "Original", right_on = celeb_type, how= "inner")
            df_final = pd.merge(df_final,df4,left_on = "Duplicates", right_on = celeb_type ,how= "inner")
            df_final = remove_duplicates(df_final)
            df_final = remove_cross_duplicates(df_final) 
            excel_file = 'output.xlsx'
            new = pd.merge(df_final, master_df, left_on = 'Original', right_on = 'Person Name', how='inner')
            new_2 = pd.merge(new, master_df, left_on = 'Duplicates', right_on = 'Person Name', how='inner')
            if celeb_type == 'Personality':
                columns = ['Original',  'Status_x', 'Total Count_x', 'Duplicates', 'Status_y', 'Total Count_y', 'Ratio', 'n_sim', 'n_sim2', 'n_sim3']
            else:
                columns = ['Original',  'Status_x', 'Total Count_x', 'Duplicates', 'Status_y', 'Total Count_y','Channel Name_x','Channel Name_y', 'Ratio', 'n_sim', 'n_sim2', 'n_sim3']
            excel_file = 'output.xlsx'
            last_df = new_2[columns]
            last_df = remove_duplicates(last_df)
            last_df = remove_cross_duplicates(last_df)
            last_df.to_excel(excel_file, sheet_name='Sheet1', index=False)
            return send_file(excel_file, as_attachment=True)
        return render_template('master_celeb.html')