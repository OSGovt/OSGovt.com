// OSGovt.com: static files from ../../public, served by Cloudflare. This small
// Worker runs first only to send http:// and www. visitors to https://osgovt.com.
// Other hosts (local development) are served as they are.
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const site = new URL(env.SITE_URL || "https://osgovt.com");
    const isWww = url.hostname === `www.${site.hostname}`;
    const isPlainHttp = url.hostname === site.hostname && url.protocol === "http:";
    if (isWww || isPlainHttp) {
      return Response.redirect(`${site.origin}${url.pathname}${url.search}`, 301);
    }
    return env.ASSETS.fetch(request);
  },
};
