<StyledLayerDescriptor xmlns="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="1.0.0" xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd">
  <NamedLayer>
    <Name>Data Quality</Name>
    <UserStyle>
      <Title>Data Quality</Title>
      <FeatureTypeStyle>
         <Rule>
           <Name>Good</Name>
           <Title>Good</Title>
           <ogc:Filter>
           <ogc:PropertyIsEqualTo>
             <ogc:PropertyName>quality</ogc:PropertyName>
             <ogc:Literal>1</ogc:Literal>
           </ogc:PropertyIsEqualTo>
           </ogc:Filter>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#00FF00</CssParameter>
             </Fill>

             </Mark>
             <Size>1</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>
         
        <Rule>
           <Name>Moderate</Name>
           <Title>Moderate</Title>
           <ogc:Filter>
           <ogc:PropertyIsEqualTo>
             <ogc:PropertyName>quality</ogc:PropertyName>
             <ogc:Literal>2</ogc:Literal>
           </ogc:PropertyIsEqualTo>
           </ogc:Filter>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#FFFF00</CssParameter>
             </Fill>
             </Mark>
             <Size>1</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>
     
        <Rule>
           <Name>Derived</Name>
           <Title>Derived</Title>
           <ogc:Filter>
           <ogc:PropertyIsEqualTo>
             <ogc:PropertyName>quality</ogc:PropertyName>
             <ogc:Literal>3</ogc:Literal>
           </ogc:PropertyIsEqualTo>
           </ogc:Filter>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#FF0000</CssParameter>
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
           <ogc:PropertyIsNull>
             <ogc:PropertyName>quality</ogc:PropertyName>
           </ogc:PropertyIsNull>
           </ogc:Filter>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#C0C0C0</CssParameter>
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