from text_summarizer import wrap_summary
from app.irsystem.controllers.case_ranking import rank_cases
import math
import json
import numpy as np
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from . import *
from app.irsystem.models.helpers import *
from app.irsystem.models.helpers import NumpyEncoder as NumpyEncoder
import os
print(os.getcwd())

project_name = "Can I Sue?"
net_id = "Junan Qu (jq77), Zachary Shine (zs92), Ian Paul (ijp9), Max Chen (mlc294), Nikhil Saggi (ns739)"

r = requests.get(
    "https://storage.googleapis.com/can_i_sue_reddit/reddit_data.json")
data = r.json()
print("loaded reddit data")

# =====REDDIT COSINE======

# title, id, selftext, url, created_utc e60m7


def get_sim(q_vector, post_vector):
    num = q_vector.dot(post_vector)
    den = np.multiply(np.sqrt(q_vector.dot(q_vector)),
                      np.sqrt(post_vector.dot(post_vector)))
    return num/den


# =====END=======


@irsystem.route('/about.html')
def go_to_about():
    return render_template('about.html')


@irsystem.route('/', methods=['GET'])
def search():
    # Search Query
    query = request.args.get('search')
    # Jurisdiction level ('Federal' or state abbreviation)
    jurisdiction = request.args.get('state')
    minimum_date = request.args.get('earliestdate')
    print(query)
    print(jurisdiction)
    print(minimum_date)
    output_message = ''
    if not query:
        res = []
        output_message = ''
        print('no query')
        return render_template('search.html', name=project_name, netid=net_id, output_message=output_message, data=res)
    else:
        # =====Reddit cos processing START=========
        # title, id, selftext, url, created_utc e60m7
        num_posts = len(data)
        index_to_posts_id = {index: post_id for index,
                             post_id in enumerate(data)}
        print('created index')
        n_feats = 5000
        # doc_by_vocab = np.empty([len(data)+1, n_feats])
        print('initialize numpy array')
        tfidf_vec = TfidfVectorizer(min_df=.01,
                                    max_df=0.8,
                                    max_features=n_feats,
                                    stop_words='english',
                                    norm='l2')
        print("initialize vectorizer")

        # d_array = [str(data[d]['selftext'])+str(data[d]['title']) for d in data]
        d_array = []
        for d in data:
            s = str(data[d]['selftext'])+str(data[d]['title'])
            d_array.append(s)

        print("built d_array")
        d_array.append(query)
        print("concatenated text and query")
        doc_by_vocab = tfidf_vec.fit_transform(d_array).toarray()
        print('to array')
        sim_posts = []
        for post_index in range(num_posts):
            # score = get_sim(doc_by_vocab[post_index], doc_by_vocab[num_posts])
            q_vector = doc_by_vocab[post_index]
            post_vector = doc_by_vocab[num_posts]
            num = q_vector.dot(post_vector)
            den = np.multiply(np.sqrt(q_vector.dot(q_vector)),
                              np.sqrt(post_vector.dot(post_vector)))
            score = num/den
            sim_posts.append((score, post_index))
        print('calculated similarities')
        sim_posts.sort(key=lambda x: x[0], reverse=True)
        print('sorted similarities')
        res = []
        for k in range(10):
            e = data[index_to_posts_id[sim_posts[k][1]]]
            e.update({"score": round(sim_posts[k][0], 3)})
            res.append(e)
        print('added results')
        # =====Reddit cos processing END=========
        print('retrieved reddit cases')
        # =====CaseLaw Retrieval=====
        print('begin caselaw retrieval')
        caselaw, debug_msg = rank_cases(
            query, jurisdiction=jurisdiction, earlydate=minimum_date)
        error = False
        if not caselaw:
            # API call to CAP failed
            caseresults = [-1]
            error = True
        else:
            caseresults = caselaw[0:5]
            # Score to keep to 3 decimals
            for case in caseresults:
                case['score'] = round(case['score'], 3)
                case['fulltext'] = case['case_summary']
            # caseresults = wrap_summary(caseresults)
            for case in caseresults:
                if not case['case_summary']:  # if case has no summary
                    case['case_summary'] = "No case summary found"
                    continue
                case['case_summary'] = case['case_summary'][0:min(
                    1000, len(case['case_summary']))]
                if len(case['case_summary']) == 1000:
                    case['case_summary'] = case['case_summary'] + '...'
        # =====Processing results================
        print('completed caselaw retrieval')
        for i in range(5):
            post = res[i]
            if (post['selftext'] is not None) and (len(post['selftext'])) > 500:
                post['selftext'] = post['selftext'][0:500] + '...'

        caselaw_message = "Historical precedences:"
        output_message = "Past discussions:"
        print('rendering template..')
        # ============================

        return render_template('search.html', name=project_name, netid=net_id,
                               output_message=output_message, data=res[:5], casedata=caseresults,
                               caselaw_message=caselaw_message,
                               user_query=query, debug_message=debug_msg,
                               is_error=error)


@irsystem.route('/about', methods=['GET'])
def about():
    return render_template('about.html')
