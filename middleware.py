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
            "title": "Al Hadar Mumuni",
            "description": "Hi, I’m Al-Hadar Mumuni, a writer, researcher, and public speaker passionate about intercultural communication, migration, employee engagement and social impact. This site shares my blogs, academic work, conference journeys, and motivational stories. Join me as I explore ideas that inspire, inform, and connect!",
            "keywords": "Communication, Intercultural, Research, Writer, Public Speaker",
            "image": url_for('static', filename='img/metaimageog.jpg', _external=True),
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
            g.seo["title"] = "About - Al Hadar Mumuni"
            g.seo["description"] = "Learn more about Al Hadar Mumuni."

        elif request.endpoint == "contact":
            g.seo["title"] = "Contact - Al Hadar Mumuni"
            g.seo["description"] = "Get in touch with Al Hadar Mumuni."
