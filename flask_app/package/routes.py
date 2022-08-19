import flask
from flask import render_template, url_for, redirect, flash, request, Blueprint
from werkzeug.utils import secure_filename
from package import app
from package.forms import textbox, fileupload, ID
from html2text import html2text
import json
import os
from wtforms import form
import requests_oauthlib
import pickle
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO
import base64
#################### REDDIT ##################
import praw 

with open("reddit_secrets.txt") as fr:
    secrets_reddit = json.load(fr)

reddit_API = praw.Reddit(client_id=secrets_reddit['client_id'], 
						client_secret=secrets_reddit['client_secret'], 
						user_agent=secrets_reddit['user_agent'],
						check_for_async=False)

#################### TWITTER ##################
from requests_oauthlib import OAuth1
import requests
import re

with open("twitter_secrets.txt") as ft:
    secrets_twitter = json.load(ft)
auth = OAuth1(
    secrets_twitter['API_Key'],
    secrets_twitter["API_Key_Secret"],
    secrets_twitter["Access_Token"],
    secrets_twitter["Access_Token_Secret"]
)

bearer_token = secrets_twitter["Bearer_Token"]

def id_by_user(username):
	usernames = "usernames={}".format(username)
	user_fields = "user.fields=description,created_at"
	url = "https://api.twitter.com/2/users/by?{}&{}".format(usernames, user_fields)
	def bearer_oauth(r):
		r.headers["Authorization"] = f"Bearer {bearer_token}"
		return r
	return requests.request("GET", url, auth=bearer_oauth).json()['data'][0]['id']

def tweet(user_id):
	url = "https://api.twitter.com/2/users/{}/tweets".format(user_id)
	query_params = {'max_results':'100'}
	def bearer_oauth(r):
		r.headers["Authorization"] = f"Bearer {bearer_token}"
		return r
	response = requests.request("GET", url, auth=bearer_oauth, params=query_params).json()

	if 'data' in response:
		texts = [x['text'] for x in response['data']]
		re1 = [re.sub('^RT ','',x) for x in texts]
		re2 = [re.sub('\@\w*: ','',x) for x in re1]
		re3 = [re.sub('\@\w*','',x).strip() for x in re2]
		return re3
	else:
		raise Exception
###############################################################################

@app.route('/')
@app.route('/index/')
@app.route('/home/')
def home():
    return render_template('home.html', title='WordPsych-home')

@app.route('/text/', methods=['GET', 'POST'])
def text():
	form = textbox()
	text = html2text(str(form.txt))
	if form.validate_on_submit():
		return redirect(url_for('results', text=text))
	return render_template('text.html', form=form, title='WordPsych-text')


@app.route('/file/', methods=['GET', 'POST'])
def file():
	form = fileupload()
	if form.validate_on_submit():
		f = form.file.data
		filename = f.filename
		text = f.read()
		return redirect(url_for('results', text=text))
	return render_template('file.html', form=form, title='WordPsych-file')


@app.route('/results/', methods=['GET', 'POST'])
def results():
	text = request.args.get('text')
	if not text:
		text = 'No Text was provided'
		return render_template('results.html', text = text, title='WordPsych-results')
	else:
		d={'general':'Non-specified mental health issue',
		'control':'No apparent mental health issue',
		'adhd':'Attention-Deficit/Hyperactivity Disorder',
		'autism':'Autism Spectrum Disorders including Aspergers',
		'anxiety':'Generalized Anxiety Disorder',
		'phobia':'Specific Phobias and Agoraphobia',
		'socialanxiety': 'Social Anxiety', 
		'ptsd': 'Post traumatic stress disorder',
		'depression':'Major Depressive Disorder',
		'sadness':'General sadness, not necessarily clinical',
		'bipolar':'Manic-Depressive Disorder',
		'ocd': 'Obsessive-Compulsive Disorder',
		'schizophrenia':'Schizophrenia, Paranoid Schizophrenia, and SchizoAffective Disorders',
		'cluster_a':'Cluster A Personality disorders: Schizoid, Schizotypal, and Paranoid',
		'cluster_b':'Cluster B Personality disorders: Borderline, Narcissistic, Antisocial, and Histrionic',
		'cluster_c':'Cluster C Personality disorders: Avoidant, Dependent, and Obsessive-Compulsive',
		'selfharm':'Selfharm and Suicidal tendencies',
		'addiction':'Alcoholism and Substance dependence',
		'eating':'Eating disorders including Bulimia, Anorexia Nervosa, and ARFID (Avoidant/Restrictive Food Intake Disorder)',
		'dpdr':'DePersonalization/DeRealization Disorder',
		'dysmorphic':'Body Dysmorphic Disorder and body acceptance issues',
		'tourettes':'Tourette Syndrome',
		'anger':'Anger Control issues'}

		hash_tfi = pickle.load(open('hash_tfi_800.pkl', 'rb'))
		clf = pickle.load(open('MNB_stop_Bi_Tfi_N9613_L500_0.213.pkl', 'rb'))
		labels = list(clf.classes_)
		x_tr = hash_tfi.transform([text])
		pred = [round(x,12) for x in clf.predict_proba(x_tr)[0]]
		lst = sorted(zip(labels, pred), key=lambda x:-x[1])
		labels = [x for x,y in lst]
		pred = [y for x,y in lst]
		desc = [d[x] for x in labels]
		my_cmap = plt.get_cmap("Set2")
		rescale = lambda y: (y - min(y)) / (max(y) - min(y))
		plt.figure(figsize=(9.1,6))
		plt.bar(labels, pred, color=my_cmap(rescale(pred)))
		plt.xticks(rotation = 70)
		plt.tight_layout()
		img = BytesIO()
		plt.savefig(img, format='png')
		plt.close()
		img.seek(0)
		plot_url = base64.b64encode(img.getvalue()).decode('utf8')
		return render_template('results.html', text=text, pred=pred, desc=desc,
								labels=labels, counts=list(range(len(labels))),
								plot_url=plot_url, title='WordPsych-results')

@app.route('/reddit/', methods=['GET', 'POST'])
def reddit():
	form = ID()
	if form.validate_on_submit():
		author = form.user.data
		try:
			submissions = []
			for sub in reddit_API.redditor(author).submissions.new(limit=40):
				submissions.append(sub)

			comments = []
			for com in reddit_API.redditor(author).comments.new(limit=80):
				comments.append(com)

			texts_sub = [x.title+' '+x.selftext for x in submissions]
			texts_com = [x.body for x in comments]
			texts = texts_sub + texts_com
		except: 
			flash("reddit ID \"{}\" does not exist.".format(author), category="error")
			return redirect(url_for('reddit'))

		return redirect(url_for('pick', lst = texts))
	return render_template('reddit.html', form=form, title='WordPsych-reddit')


@app.route('/pick/', methods=['GET', 'POST'])
def pick():
	lst = request.args.getlist('lst')
	if request.method == 'POST':
		selected = request.form.getlist('multi')
		text =''
		for i in selected:
			text += lst[int(i)]+'. '
		return redirect(url_for('results', text = text))
	return render_template('pick.html', counts = list(range(len(lst))), choices=lst, title='WordPsych-pick')


@app.route('/twitter/', methods=['GET', 'POST'])
def twitter():
	form = ID()
	if form.validate_on_submit():
		id = form.user.data
		try:
			texts = tweet(id)
		except: 
			flash("twitter ID number \"{}\" does not exist.".format(id), category="error")
			return redirect(url_for('twitter'))
		return redirect(url_for('pick', lst = texts))
	return render_template('twitter.html', form=form, title='WordPsych-twitter')


@app.route('/twitter2/', methods=['GET', 'POST'])
def twitter2():
	form = ID()
	if form.validate_on_submit():
		username = form.user.data
		try:
			id = id_by_user(username)
		except: 
			flash("twitter username \"{}\" does not exist.".format(username), category="error")
			return redirect(url_for('twitter2'))
		try:
			texts = tweet(id)
		except:
			flash("twitter username \"{}\" does not exist.".format(username), category="error")
			return redirect(url_for('twitter2'))
		return redirect(url_for('pick', lst = texts))
	return render_template('twitter2.html', form=form, title='WordPsych-twitter')


@app.route('/what/')
def what():
	return render_template('what.html', title='WordPsych-what')


@app.route('/why/')
def why():
	return render_template('why.html', title='WordPsych-why')


@app.route('/dataset/')
def dataset():
    lst = [
    ('depression', 11.304),
    ('adhd', 12.304),
    ('anxiety', 10.271),
    ('autism', 10.315),
    ('cluster_b', 6.026),
    ('bipolar', 5.027),
    ('ptsd', 5.818),
    ('socialanxiety', 3.419),
    ('general', 3.327),
    ('control', 3.229),
    ('selfharm', 2.43),
    ('addiction', 2.76),
    ('ocd', 2.603),
    ('eating', 2.626),
    ('schizophrenia', 1.901),
    ('sadness', 0.997),
    ('phobia', 1.062),
    ('dysmorphic', 0.97),
    ('dpdr', 0.808),
    ('anger', 0.762),
    ('cluster_a', 0.617),
    ('tourettes', 0.413),
    ('cluster_c', 0.203)]
    LST = [('depression', 139.531461),
    ('adhd', 125.45403),
    ('anxiety', 115.9),
    ('autism', 101.039804),
    ('cluster_b', 60.288147),
    ('bipolar', 51.590906),
    ('ptsd', 47.698102),
    ('socialanxiety', 43.7),
    ('general', 36.424827),
    ('control', 32.777371),
    ('selfharm', 32.623954),
    ('addiction', 31.83386),
    ('ocd', 28.456335),
    ('eating', 27.973656),
    ('schizophrenia', 20.126049),
    ('sadness', 18.774087),
    ('phobia', 11.817137),
    ('dysmorphic', 8.976985),
    ('dpdr', 8.6),
    ('anger', 8.565897),
    ('cluster_a', 5.639788),
    ('tourettes', 4.98961),
    ('cluster_c', 1.727758)]
    plt.figure(figsize=(9.1,6))
    plt.bar(list(map(lambda x:x[0], LST)),list(map(lambda x:x[1], LST)), label = 'all texts', alpha=.7)
    plt.bar(list(map(lambda x:x[0], LST)),list(map(lambda x:x[1], lst)), label = 'text_length > 500 characters')
    plt.legend()
    plt.title('Sample size per groups: There are quite large imbalances in our dataset')
    plt.ylabel('sample size (millions)')
    plt.xticks(rotation = 70)
    plt.tight_layout()
    img2 = BytesIO()
    plt.savefig(img2, format='png')
    plt.close()
    img2.seek(0)
    plot_url = base64.b64encode(img2.getvalue()).decode('utf8')
    return render_template('dataset.html', plot_url=plot_url, title='WordPsych-data')


@app.route('/how/')
def how():
    return render_template('how.html',  title='WordPsych-how')


@app.route('/tryit/')
def tryit():
	return render_template('tryit.html', title='WordPsych-tryit')


@app.route('/contact/')
def contact():
	return render_template('contact.html', title='WordPsych-contact')
