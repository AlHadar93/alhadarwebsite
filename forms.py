# Import required libraries
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, EmailField, DateField, TimeField
from wtforms.validators import DataRequired, EqualTo, Email, Length, Regexp, Optional
from flask_ckeditor import CKEditorField


# Form to submit a post
class CreatePostForm(FlaskForm):
    title = StringField("Blog Post Title", validators=[DataRequired()])
    img_url = StringField("Image URL", validators=[DataRequired()])
    body = CKEditorField("Blog Content", validators=[DataRequired()])
    category = StringField("Category", validators=[DataRequired()])

    # Add these as form fields instead of handling them separately
    publish_date = DateField('Publish Date', format='%Y-%m-%d', validators=[Optional()])
    publish_time = TimeField('Publish Time', validators=[Optional()])

    publish = SubmitField("Publish Your Post Now!")
    draft = SubmitField("Save Your Post as Draft!")
    schedule = SubmitField("Schedule Your Post!")
    update_post = SubmitField("Update your post!")

    def validate(self, extra_validators=None):
        """Validate the form."""
        initial_validation = super().validate(extra_validators)
        if not initial_validation:
            return False

        if self.schedule.data:
            if not self.publish_date.data:
                self.publish_date.errors = ['Publish date is required when scheduling a post.']
                return False
            if not self.publish_time.data:
                self.publish_time.errors = ['Publish time is required when scheduling a post.']
                return False

        return True

# Form to register to leave a comment as a user
class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long.'),
        Regexp(r'(?=.*[0-9])', message='Password must contain at least one number.'),
        Regexp(r'(?=.*[!@#$%^&*(),.?":{}|<>])', message='Password must contain at least one special character.')
    ])
    name = StringField("Name", validators=[DataRequired()])
    submit = SubmitField("Sign Me Up!")


# Form to log in as an existing user
class LogInForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long.'),
        Regexp(r'(?=.*[0-9])', message='Password must contain at least one number.'),
        Regexp(r'(?=.*[!@#$%^&*(),.?":{}|<>])', message='Password must contain at least one special character.')
    ])
    submit = SubmitField("Let Me In")


# The comment form
class CommentForm(FlaskForm):
    comment = StringField("Comment", validators=[DataRequired()])
    submit = SubmitField("Leave a comment!")

# Form to request a password reset
class ForgotPasswordForm(FlaskForm):
    email = EmailField("Enter your registered email", validators=[DataRequired(), Email()])
    submit = SubmitField("Send Reset Link")

# Form to reset the password
class ResetPasswordForm(FlaskForm):
    new_password = PasswordField("New Password", validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long.'),
        Regexp(r'(?=.*[0-9])', message='Password must contain at least one number.'),
        Regexp(r'(?=.*[!@#$%^&*(),.?":{}|<>])', message='Password must contain at least one special character.')
    ])

    confirm_password = PasswordField("Confirm New Password", validators=[DataRequired(), EqualTo('new_password', message="Passwords must match")])
    submit = SubmitField("Reset Password")
