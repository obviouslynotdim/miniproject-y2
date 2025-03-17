from asyncio import Task
from flask import render_template, request, redirect, url_for, flash
from portfolio import db, app, bcrypt
from portfolio.forms import RegisterForm, LoginForm, UpdateAccountForm
from portfolio.models import User, Friend
from flask_login import login_user, logout_user, current_user, login_required
import os, secrets
from PIL import Image

@app.route('/')
def home():
    page = request.args.get('page', type=int)
    friends = db.paginate(db.select(Friend), per_page=8, page=page)
    return render_template('index.html', 
                           title='Home Page', 
                           friends=friends)

@app.route('/user/register', methods=['GET', 'POST'])
def register():
  form = RegisterForm()
  if form.validate_on_submit():
    username = form.username.data
    email = form.email.data
    password = form.password.data
    hash_password = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(username=username, email=email, password=hash_password)

    db.session.add(user)
    db.session.commit()

    return redirect(url_for('login'))
  
  return render_template('user/register.html', title='Register Page', form=form)

@app.route('/user/login', methods=['GET', 'POST'])
def login():
  form = LoginForm()
  if form.validate_on_submit():
    username = form.username.data
    password = form.password.data
    remember = form.remember.data

    user = db.session.scalar(db.select(User).where(User.username==username))

    if user and bcrypt.check_password_hash(user.password, password):
      login_user(user=user, remember=remember)
      return redirect(url_for('home'))
  return render_template('user/login.html', title='Login Page', form=form)

@app.route('/user/logout')
@login_required
def logout():
  logout_user()
  return redirect(url_for('login'))

def save_avatar(form_avatar):
  random_hex = secrets.token_hex(8)
  _, ext = os.path.splitext(form_avatar.filename)
  avatar_fn = random_hex + ext

  avatar_path = os.path.join(app.root_path, 'static/img', avatar_fn)

  img_size = (256, 256)
  img = Image.open(form_avatar)
  img.thumbnail(img_size)
  img.save(avatar_path)

  return avatar_fn

@app.route('/user/account', methods=['GET', 'POST'])
@login_required
def account():
  form = UpdateAccountForm()
  if request.method == 'GET':
    form.username.data = current_user.username
    form.email.data = current_user.email
    form.fullname.data = current_user.fullname
  elif form.validate_on_submit():
    if form.avatar.data:
      avatar = save_avatar(form.avatar.data)
      current_user.avatar = avatar
    current_user.fullname = form.fullname.data
    db.session.commit()
    return redirect(url_for('account'))
  avatar_pic = current_user.avatar
  return render_template('user/account.html', title='Account Info Page', form=form, avatar_pic=avatar_pic)

@app.route('/profile/friend', methods=['GET', 'POST'])
def friend():
    search_query = None
    if request.method == 'POST':
        search_query = request.form.get('friend_name', '').strip()
    
    if search_query:
        friends = db.session.scalars(db.select(Friend).where(Friend.name.ilike(f'%{search_query}%'))).all()
    else:
        friends = db.session.scalars(db.select(Friend)).all()

    return render_template('profile/index.html', title='Friend Profile Page', friends=friends, search_query=search_query)

@app.route('/profile/friend/<int:id>')
def friend_detail(id):
  friend = db.session.get(Friend, id)
  if friend is None:
      flash("Friend not found", "warning")
      return redirect(url_for('friend'))
  return render_template('profile/detail.html', friend=friend)


@app.route('/profile/friend/new_profile', methods=['GET', 'POST'])
@login_required
def new_profile():
    if request.method == 'POST':
        name = request.form.get('friend_name')
        friend_details = request.form.get('friend_details')
        img_url = request.form.get('img_url')

        if not name:
            flash('Friend name is required!', 'danger')
            return render_template('profile/new_profile.html', title='Friend Page')

        friend = db.session.scalar(db.select(Friend).where(Friend.name == name))
        if friend:
            flash('Friend already exists!', 'warning')
        else:
            friend = Friend(name=name,
                friend_details=friend_details,
                img_url=img_url,
                user_id=current_user.id)

            db.session.add(friend)
            db.session.commit()
            flash('New friend added successfully!', 'success')
            return redirect(url_for('friend'))

    return render_template('profile/new_profile.html', title='Friend Page')

@app.route('/profile/friend/delete/<int:id>', methods=['POST'])
@login_required
def delete_friend(id):
    friend = db.session.get(Friend, id)
    if friend:
        db.session.delete(friend)
        db.session.commit()
        flash('Friend deleted successfully', 'success')
    else:
        flash('Friend not found', 'danger')
    return redirect(url_for('friend'))

@app.route('/profile/friend/delete_all', methods=['POST'])
@login_required
def delete_all_friends():
    try:
        db.session.query(Friend).filter(Friend.user_id == current_user.id).delete()
        db.session.commit()
        flash('All friends have been deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error occurred: {e}', 'danger')
    return redirect(url_for('friend'))

@app.route('/profile/friend/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_friend(id):
    friend = db.session.get(Friend, id)
    if friend is None:
        flash("Friend not found", "warning")
        return redirect(url_for('friend'))

    if request.method == 'POST':
        friend.name = request.form.get('friend_name')
        friend.friend_details = request.form.get('friend_details')
        friend.img_url = request.form.get('img_url')

        if not friend.name:
            flash('Friend name is required!', 'danger')
            return render_template('profile/edit_profile.html', title='Edit Friend Page', friend=friend)

        db.session.commit()
        flash('Friend details updated successfully!', 'success')
        return redirect(url_for('friend_detail', id=friend.id))

    return render_template('profile/edit_profile.html', title='Edit Friend Page', friend=friend)
