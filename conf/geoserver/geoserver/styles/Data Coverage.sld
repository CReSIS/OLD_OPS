<StyledLayerDescriptor xmlns="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="1.0.0" xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd">
  <NamedLayer>
    <Name>Data Exists</Name>
    <UserStyle>
      <Title>Data Exists</Title>
      <FeatureTypeStyle>
        <Rule>
           <Name>Picked</Name>
           <Title>Picked</Title>
           <ogc:Filter>
           <ogc:PropertyIsEqualTo>
             <ogc:PropertyName>exists</ogc:PropertyName>
             <ogc:Literal>1</ogc:Literal>
           </ogc:PropertyIsEqualTo>
           </ogc:Filter>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#0000FF</CssParameter>
             </Fill>
             </Mark>
             <Size>1</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>
        
        <Rule>
           <Name>Not Picked</Name>
           <Title>Not Picked</Title>
           <ogc:Filter>
           <ogc:PropertyIsEqualTo>
             <ogc:PropertyName>exists</ogc:PropertyName>
             <ogc:Literal>0</ogc:Literal>
           </ogc:PropertyIsEqualTo>
           </ogc:Filter>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#66FFFF</CssParameter>
             </Fill>
             </Mark>
             <Size>1</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>
     
         </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>