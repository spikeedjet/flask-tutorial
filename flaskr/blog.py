from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from flaskr.auth import login_required
from flaskr.db import get_db
import sqlite3
from flask import session

bp = Blueprint('blog', __name__)

@bp.route('/')
def index():
    db = get_db()
    posts = db.execute(
        'SELECT p.id, title, body, created, author_id, likes,username'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' ORDER BY created DESC'
    ).fetchall()
    print(posts)
    return render_template('blog/index.html', posts=posts)

@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO post (title, body, author_id)'
                ' VALUES (?, ?, ?)',
                (title, body, g.user['id'])
            )
            db.commit()
            return redirect(url_for('blog.index'))

    return render_template('blog/create.html')

def get_post(id, check_author=True):
    post = get_db().execute(
        'SELECT p.id, title, body, created, author_id, username'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' WHERE p.id = ?',
        (id,)
    ).fetchone()

    if post is None:
        abort(404, f"Post id {id} doesn't exist.")

    # if check_author and post['author_id'] != g.user['id']:
    #     abort(403)

    return post

@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    post = get_post(id)

    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE post SET title = ?, body = ?'
                ' WHERE id = ?',
                (title, body, id)
            )
            db.commit()
            return redirect(url_for('blog.index'))

    return render_template('blog/update.html', post=post)


@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_post(id)
    db = get_db()
    db.execute('DELETE FROM post WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('blog.index'))

@bp.route('/post/<int:id>', methods=('GET',))
def details(id):
    db = get_db()
    post = get_post(id)
    return render_template('blog/details.html', post=post)

@bp.route('/post/<int:id>/like', methods=('POST','GET'))
@login_required
def like_post(id):
    db = get_db()
    if 'user_id' in session:
        user_id = session['user_id']
        # 这里可以继续处理点赞逻辑，使用 user_id 进行操作        
        try:
            user_like = db.execute(
            'SELECT id FROM likes WHERE user_id = ? AND post_id = ?',(user_id, id)
            ).fetchone()
            if user_like:
                # User has already liked this post, so we remove the like
                db.execute('DELETE FROM likes WHERE user_id = ? AND post_id = ?', (user_id, id))
                db.execute('UPDATE post SET likes = likes - 1 WHERE id = ?', (id,))
                db.commit()
            else:
                # User has not liked this post, so we add the like
                db.execute('INSERT INTO likes (user_id, post_id) VALUES (?, ?)', (user_id, id))
                db.execute('UPDATE post SET likes = likes + 1 WHERE id = ?', (id,))
                db.commit()
        except sqlite3.IntegrityError:
            # IntegrityError indicates duplicate like record
            pass
        finally:
            pass
        return redirect(url_for('blog.index'))
    
    else:
        # 如果用户未登录，可以返回错误或跳转到登录页面
        return render_template('auth/login.html')

 