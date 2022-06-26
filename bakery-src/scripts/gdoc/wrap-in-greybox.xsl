<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:h="http://www.w3.org/1999/xhtml"
  xmlns="http://www.w3.org/1999/xhtml"
  exclude-result-prefixes="h">

<xsl:template match="@*|node()">
  <xsl:copy>
    <xsl:apply-templates select="@*|node()"/>
  </xsl:copy>
</xsl:template>

<xsl:template match="*[@data-type='note']">
  <xsl:call-template name="wrapper">
    <xsl:with-param name="label">NOTE</xsl:with-param>
  </xsl:call-template>
</xsl:template>

<xsl:template match="*[@data-type='example']">
  <xsl:call-template name="wrapper">
    <xsl:with-param name="label">EXAMPLE</xsl:with-param>
  </xsl:call-template>
</xsl:template>

<xsl:template match="h:h1" mode="grey">
  <div custom-style="Heading1Grey">
    <p>
      <xsl:apply-templates select="@*|node()" mode="grey"/>
    </p>
  </div>
</xsl:template>

<xsl:template match="h:h2" mode="grey">
  <div custom-style="Heading2Grey">
    <p>
      <xsl:apply-templates select="@*|node()" mode="grey"/>
    </p>
  </div>
</xsl:template>

<xsl:template match="h:h3" mode="grey">
  <div custom-style="Heading3Grey">
    <p>
      <xsl:apply-templates select="@*|node()" mode="grey"/>
    </p>
  </div>
</xsl:template>

<xsl:template match="h:h4" mode="grey">
  <div custom-style="Heading4Grey">
    <p>
      <xsl:apply-templates select="@*|node()" mode="grey"/>
    </p>
  </div>
</xsl:template>

<xsl:template match="h:h5" mode="grey">
  <div custom-style="Heading5Grey">
    <p>
      <xsl:apply-templates select="@*|node()" mode="grey"/>
    </p>
  </div>
</xsl:template>

<xsl:template match="h:h6" mode="grey">
  <div custom-style="Heading6Grey">
    <p>
      <xsl:apply-templates select="@*|node()" mode="grey"/>
    </p>
  </div>
</xsl:template>

<xsl:template match="h:h7" mode="grey">
  <div custom-style="Heading7Grey">
    <p>
      <xsl:apply-templates select="@*|node()" mode="grey"/>
    </p>
  </div>
</xsl:template>

<xsl:template match="h:h8" mode="grey">
  <div custom-style="Heading8Grey">
    <p>
      <xsl:apply-templates select="@*|node()" mode="grey"/>
    </p>
  </div>
</xsl:template>

<xsl:template match="h:h9" mode="grey">
  <div custom-style="Heading9Grey">
    <p>
      <xsl:apply-templates select="@*|node()" mode="grey"/>
    </p>
  </div>
</xsl:template>

<xsl:template match="h:div|h:section" mode="grey">
  <xsl:copy>
    <xsl:attribute name="custom-style">NoteExampleGrey</xsl:attribute>
    <xsl:apply-templates select="@*|node()" mode="grey"/>
  </xsl:copy>
</xsl:template>

<!-- make block math to inline because of Google Docs styling bug -->
<!-- note: pandoc ignores text center property https://github.com/jgm/pandoc/issues/719 -->
<xsl:template match="h:math[@display='block']" mode="grey">
  <div>
  <p style="text-align:center">
    <xsl:copy>
      <xsl:attribute name="display">inline</xsl:attribute>
      <xsl:apply-templates select="@*[name()!='display']|node()" mode="grey"/>
    </xsl:copy>
  </p>
  </div>
</xsl:template>

<!-- make block math to inline also for non grey background math -->
<!-- note: pandoc ignores text center property https://github.com/jgm/pandoc/issues/719 -->
<xsl:template match="h:math[@display='block']">
  <div>
  <p style="text-align:center">
    <xsl:copy>
      <xsl:attribute name="display">inline</xsl:attribute>
      <xsl:apply-templates select="@*[name()!='display']|node()" mode="grey"/>
    </xsl:copy>
  </p>
  </div>
</xsl:template>

<xsl:template match="@*|node()" mode="grey">
  <xsl:copy>
    <xsl:apply-templates select="@*|node()" mode="grey"/>
  </xsl:copy>
</xsl:template>

<xsl:template name="wrapper">
  <xsl:param name="label"/>
  <!-- add a paragraph with hard space/NBSP if another "grey box" was preceding  -->
  <xsl:if test="preceding-sibling::*[1][@data-type='note' or @data-type='example']">
    <div custom-style="SmallWhiteGap"><p>&#160;</p></div>
  </xsl:if>
    <div custom-style="NoteExampleGrey">
      <xsl:copy>
        <xsl:apply-templates select="@*|node()" mode="grey"/>
      </xsl:copy>
    </div>
</xsl:template>

</xsl:stylesheet>