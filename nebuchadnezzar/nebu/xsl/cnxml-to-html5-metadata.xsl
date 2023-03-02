<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:c="http://cnx.rice.edu/cnxml"
  xmlns:md="http://cnx.rice.edu/mdml"
  >

<xsl:output omit-xml-declaration="yes" encoding="ASCII"/>

<!-- ========================= -->
<!-- One-way conversions       -->
<!-- ========================= -->


<xsl:template match="c:document">
  <head>
    <xsl:apply-templates select="c:title"/>
    <xsl:apply-templates select="c:metadata"/>
  </head>
</xsl:template>

<xsl:template match="c:metadata">
  <xsl:apply-templates select="md:*"/>
</xsl:template>




<xsl:template match="md:created">
  <meta name="created-time" content="{.}"/>
</xsl:template>

<xsl:template match="md:revised">
  <meta name="revised-time" content="{.}"/>
</xsl:template>

<xsl:template match="md:license">
  <meta name="license" content="{@url}"/>
</xsl:template>

<xsl:template match="md:keywordlist">
  <xsl:variable name="keywords">
    <xsl:apply-templates select="md:keyword"/>
  </xsl:variable>
  <meta name="keywords" content="{$keywords}"/>
</xsl:template>

<xsl:template match="md:keywordlist/md:keyword">
  <xsl:if test="position() != 1">
    <xsl:text>, </xsl:text>
  </xsl:if>
  <xsl:value-of select="text()"/>
</xsl:template>

<xsl:template match="md:subjectlist">
  <xsl:apply-templates select="md:subject"/>
</xsl:template>

<xsl:template match="md:subjectlist/md:subject">
  <meta name="subject" content="{.}"/>
</xsl:template>


<xsl:template match="md:roles">
  <xsl:apply-templates select="md:role"/>
</xsl:template>

<xsl:template match="md:roles/md:role[@type='author']">
  <xsl:choose>
    <xsl:when test="contains(text(), ' ')">
      <xsl:message>TODO: Does not support multiple authors yet</xsl:message>
    </xsl:when>
    <xsl:otherwise>
      <meta name="author" content="{.}"/>
    </xsl:otherwise>
  </xsl:choose>
</xsl:template>

<!-- NOTE: THis should become an ACL list -->
<xsl:template match="md:roles/md:role[@type='maintainer']">
  <xsl:choose>
    <xsl:when test="contains(text(), ' ')">
      <xsl:message>TODO: Does not support multiple maintainers yet</xsl:message>
    </xsl:when>
    <xsl:otherwise>
      <meta name="acl-list" content="{.}"/>
    </xsl:otherwise>
  </xsl:choose>
</xsl:template>

<xsl:template match="md:roles/md:role[@type='licensor']">
  <xsl:choose>
    <xsl:when test="contains(text(), ' ')">
      <xsl:message>TODO: Does not support multiple licensors yet</xsl:message>
    </xsl:when>
    <xsl:otherwise>
      <meta name="licensor" content="{.}"/>
    </xsl:otherwise>
  </xsl:choose>
</xsl:template>


<xsl:template match="*">
  <xsl:message>TODO: <xsl:value-of select="name()"/></xsl:message>
</xsl:template>

<!-- Discard actor info; we just care about usernames -->
<xsl:template match="md:actors"/>

<!-- The abstract has been moved into the body -->
<xsl:template match="md:abstract"/>


<xsl:template match="md:repository|md:content-url|md:content-id|md:title|md:version|md:language"/>

<xsl:template match="c:title">
  <title><xsl:value-of select="."/></title>
</xsl:template>

</xsl:stylesheet>
