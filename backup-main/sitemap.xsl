<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:sitemap="http://www.sitemaps.org/schemas/sitemap/0.9">
  <xsl:output method="html" encoding="UTF-8" indent="yes"/>

  <xsl:template match="/">
    <html lang="en">
      <head>
        <meta charset="UTF-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
        <title>Naukri Dhaba Sitemap</title>
        <style>
          body {
            font-family: Arial, sans-serif;
            margin: 0;
            background: #f5f7fb;
            color: #1f2937;
          }
          main {
            max-width: 1100px;
            margin: 0 auto;
            padding: 32px 20px 48px;
          }
          h1 {
            margin: 0 0 8px;
            font-size: 32px;
          }
          p {
            margin: 0 0 24px;
            color: #4b5563;
          }
          table {
            width: 100%;
            border-collapse: collapse;
            background: #ffffff;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
          }
          th, td {
            padding: 14px 16px;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
            vertical-align: top;
          }
          th {
            background: #0f172a;
            color: #ffffff;
            font-size: 14px;
            letter-spacing: 0.02em;
          }
          tr:last-child td {
            border-bottom: none;
          }
          a {
            color: #0b57d0;
            text-decoration: none;
            word-break: break-all;
          }
          a:hover {
            text-decoration: underline;
          }
          .count {
            display: inline-block;
            margin-bottom: 20px;
            padding: 8px 12px;
            background: #e8f0fe;
            color: #0b57d0;
            border-radius: 999px;
            font-size: 14px;
            font-weight: 600;
          }
        </style>
      </head>
      <body>
        <main>
          <h1>Naukri Dhaba Sitemap</h1>
          <p>XML sitemap for search engines and manual inspection.</p>
          <div class="count">
            Total URLs:
            <xsl:value-of select="count(sitemap:urlset/sitemap:url)"/>
          </div>
          <table>
            <thead>
              <tr>
                <th>URL</th>
                <th>Last Modified</th>
                <th>Change Frequency</th>
                <th>Priority</th>
              </tr>
            </thead>
            <tbody>
              <xsl:for-each select="sitemap:urlset/sitemap:url">
                <tr>
                  <td>
                    <a>
                      <xsl:attribute name="href">
                        <xsl:value-of select="sitemap:loc"/>
                      </xsl:attribute>
                      <xsl:value-of select="sitemap:loc"/>
                    </a>
                  </td>
                  <td><xsl:value-of select="sitemap:lastmod"/></td>
                  <td><xsl:value-of select="sitemap:changefreq"/></td>
                  <td><xsl:value-of select="sitemap:priority"/></td>
                </tr>
              </xsl:for-each>
            </tbody>
          </table>
        </main>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
