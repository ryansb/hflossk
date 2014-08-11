"""
Author: Remy D <remyd@civx.us>
        Ralph Bean <rbean@redhat.com>
        Sam Lucidi <mansam@csh.rit.edu>
License: Apache 2.0

"""

from __future__ import division

import os
import glob
import yaml
import hashlib
from datetime import datetime, timedelta, date

# flask dependencies
from flask import Flask
from flask import jsonify
from flask.ext.mako import MakoTemplates, render_template
from werkzeug.exceptions import NotFound

# hflossk
from hflossk.util import count_posts
from hflossk.blueprints import homework, lectures, quizzes

app = Flask(__name__)
app.template_folder = "templates"
mako = MakoTemplates(app)
base_dir = os.path.split(__file__)[0]

# Automatically include site config
@app.context_processor
def inject_yaml():
    with open(os.path.join(base_dir, 'site.yaml')) as site_yaml:
        site_config = yaml.load(site_yaml)
    return site_config

app.config['MAKO_TRANSLATE_EXCEPTIONS'] = False
config = inject_yaml()
COURSE_START = datetime.combine(config['course']['start'], datetime.min.time())
COURSE_END = datetime.combine(config['course']['end'], datetime.max.time())



def gravatar(email):
    """
    Get a gravatar for an email address.

    I wish I could use libravatar here, but honestly, the students
    will be better off using gravatar at this point (due to github
    integration :/)

    """

    email = email.encode('utf8').lower()
    slug = hashlib.md5(email).hexdigest()
    libravatarURL = "https://seccdn.libravatar.org/avatar/"
    gravatarURL = "https://secure.gravatar.com/avatar/"
    return libravatarURL + slug +"?d=" + gravatarURL + slug


@app.route('/', defaults=dict(page='home'))
@app.route('/<page>')
def simple_page(page):
    """
    Render a simple page. Looks for a .mak template file
    with the name of the page parameter that was passed in.
    By default, this just shows the homepage.

    """

    return render_template('{}.mak'.format(page), name='mako')


@app.route('/syllabus')
def syllabus():
    """
    Render the syllabus page.

    """

    with open(os.path.join(base_dir, 'schedule.yaml')) as schedule_yaml:
        schedule = yaml.load(schedule_yaml)
    return render_template('syllabus.mak', schedule=schedule, name='mako')

@app.route('/blog/<username>')
def blog_posts(username):
    """
    Count number of posts on a student's
    blog.

    """

    student_data = None

    fname = username
    with open(fname) as student:
        contents = yaml.load(student)
        if not isinstance(contents, list):
            raise ValueError("%s's yaml file is broken." % fname)
        student_data = contents[0]

    num_posts = 0
    if 'feed' in student_data:
        print("Checking %s's blog feed." % username)
        num_posts = count_posts(student_data['feed'], COURSE_START)
    else:
        print("No feed listed for %s!" % username)
        raise NotFound()

    return jsonify(number=num_posts)

@app.route('/blogs/<year>/<term>/<username>')
@app.route('/participants/<year>/<term>/<username>')
@app.route('/checkblogs/<year>/<term>/<username>')
def participant_page(year, term, username):
    print year
    print term
    print username
    """
    Render a page that shows some stats about the selected participant
    """

    participant_data = {}
    yaml_dir = 'scripts/people/'
    participant_yaml = yaml_dir + year + '/' + term + '/' + username + '.yaml'
    with open(participant_yaml) as participant_data:
        participant_data = yaml.load(participant_data)
    
    return render_template(
        'participant.mak', name='make',
        participant_data=participant_data[0],
        gravatar=gravatar
    )


@app.route('/blogs/')
@app.route('/participants/')
@app.route('/checkblogs/')
def participants():
    year = str(date.today().year)
    term = "fall" if date.today().month > 7 else "spring"
    return participants_year_term(year, term)


@app.route('/blogs')
@app.route('/participants')
@app.route('/checkblogs')
def participants_raw():
    return redirect(url_for('/blogs/'))


@app.route('/blogs/<year>')
@app.route('/participants/<year>')
@app.route('/checkblogs/<year>')
def participants_year(year): return participants(year + '/')


@app.route('/blogs/<year>/<term>')
@app.route('/participants/<year>/<term>')
@app.route('/checkblogs/<year>/<term>')
def participants_year_term(year, term): return participants(year + '/' + term + '/')

@app.route('/blogs/all')
@app.route('/participants/all')
@app.route('/checkblogs/all')
def participants_all():
    return participants('')



def participants(root_dir):
    """
    Render the participants page,
    which shows a directory of all
    the students with their forge
    links, blog posts, assignment
    links, and etc.

    """

    yaml_dir = 'scripts/people/' + root_dir

    student_data = []
    for dirpath, dirnames, files in os.walk(yaml_dir):
        for fname in files:
            if fname.endswith('.yaml'):
                with open(dirpath + '/' + fname) as students:
                    contents = yaml.load(students)
                    contents[0]['yaml'] = dirpath + '/' + fname
                    year_term_data = dirpath.split('/')
                    print year_term_data
                    contents[0]['participant_page'] = year_term_data[2] + '/' + year_term_data[3] + '/' + os.path.splitext(fname)[0]

                    if not isinstance(contents, list):
                        raise ValueError("%r is borked" % fname)

                    student_data.extend(contents)

    assignments = ['litreview1']
    target_number = int((datetime.today() - COURSE_START).total_seconds() /
                        timedelta(weeks=1).total_seconds() + 1 + len(assignments))

    return render_template(
        'blogs.mak', name='mako',
        student_data=student_data,
        gravatar=gravatar,
        target_number=target_number
    )


@app.route('/oer')
@app.route('/resources')
def resources():
    resources = dict()
    resources['Decks'] = os.listdir(os.path.join(base_dir, 'static', 'decks'))
    resources['Books'] = os.listdir(os.path.join(base_dir, 'static', 'books'))
    resources['Challenges'] = os.listdir(os.path.join(base_dir, 'static', 'challenges'))
    resources['Videos'] = os.listdir(os.path.join(base_dir, 'static', 'videos'))

    return render_template('resources.mak', name='mako', resources=resources)


app.register_blueprint(homework, url_prefix='/assignments')
app.register_blueprint(homework, url_prefix='/hw')
app.register_blueprint(lectures, url_prefix='/lectures')
app.register_blueprint(quizzes, url_prefix='/quizzes')
app.register_blueprint(quizzes, url_prefix='/quiz')
