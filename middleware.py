from flask import request, g, url_for
from urllib.parse import urljoin


class SEOMiddleware:
    def __init__(self, app):
        self.app = app
        app.before_request(self.before_request)

    def before_request(self):
        """Inject dynamic SEO metadata and GTM ID into Flask global `g`."""

        # Default SEO metadata
        g.seo = {
            "title": "#YOUR SITE TITLE HERE",
            "description": "YOUR SITE DESCRIPTION HERE",
            "keywords": "YOUR SITE KEYWORKDS HERE",
            "image": url_for('static', filename='img/YOURIMAGENAME.IMAGEEXTENSION', _external=True),
            "url": request.base_url,
            "canonical": request.base_url  # Default to current URL (will override below if needed)
        }

        # Google Tag Manager ID
        g.gtm_id = "YOUR GOOGLE TAG ID"

        # Customize SEO metadata for specific pages
        if request.endpoint == "show_post":
            post = getattr(request.view_args, 'post', None)
            if post:
                g.seo["title"] = post.title
                g.seo["description"] = (post.body[:160] + "...") if post.body else "Check out this post."
                g.seo["image"] = post.img_url
                g.seo["url"] = urljoin(request.host_url,
                                       url_for('show_post', category=post.category.replace(" ", "-"), post_id=post.id))

                # Ensure canonical URL is in lowercase
                g.seo["canonical"] = urljoin(request.host_url,
                                             url_for('show_post', category=post.category.replace(" ", "-").lower(),
                                                     post_id=post.id))

        elif request.endpoint == "about":
            g.seo["title"] = "YOUR ABOUT TITLE HERE"
            g.seo["description"] = "YOUR DESCRIPTION HERE."

        elif request.endpoint == "contact":
            g.seo["title"] = "YOUR CONTACT TITLE HERE"
            g.seo["description"] = "YOUR CONTACT DESCRIPTION HERE."
