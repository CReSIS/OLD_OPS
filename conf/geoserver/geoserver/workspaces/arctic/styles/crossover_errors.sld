<StyledLayerDescriptor xmlns="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="1.0.0" xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd">
  <NamedLayer>
    <Name>Crossover Errors</Name>
    <UserStyle>
      <Title>Crossover Errors</Title>
      <FeatureTypeStyle>
    <!-- Rules for small scale -->
         <Rule>
           <Name>0-25</Name>
           <Title>0 to 25</Title>
           <ogc:Filter>
           <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>25</ogc:Literal>
           </ogc:PropertyIsLessThan>
           </ogc:Filter>
       <MaxScaleDenominator>1200000</MaxScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#0068310</CssParameter>
             </Fill>
              <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
             </Stroke>
             </Mark>
             <Size>14</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>
         <Rule>
           <Name>25-50</Name>
           <Title>25 to 50</Title>
           <ogc:Filter>
           <ogc:And>
             <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>25</ogc:Literal>
             </ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>50</ogc:Literal>
             </ogc:PropertyIsLessThan>
           </ogc:And>
           </ogc:Filter>
       <MaxScaleDenominator>1200000</MaxScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#1a9850</CssParameter>
             </Fill>
              <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
             </Stroke>
             </Mark>
             <Size>14</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>
         <Rule>
           <Name>50-75</Name>
           <Title>50 to 75</Title>
           <ogc:Filter>
           <ogc:And>
             <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>50</ogc:Literal>
             </ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>75</ogc:Literal>
             </ogc:PropertyIsLessThan>
           </ogc:And>
           </ogc:Filter>
       <MaxScaleDenominator>1200000</MaxScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#66bd63</CssParameter>
             </Fill>
             <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
             </Stroke>
             </Mark>
             <Size>14</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>   
         <Rule>
           <Name>75-100</Name>
           <Title>75 to 100</Title>
           <ogc:Filter>
           <ogc:And>
             <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>75</ogc:Literal>
             </ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>100</ogc:Literal>
             </ogc:PropertyIsLessThan>
           </ogc:And>
           </ogc:Filter>
       <MaxScaleDenominator>1200000</MaxScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#a6d96a</CssParameter>
             </Fill>
             <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
             </Stroke>
             </Mark>
             <Size>14</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>   
          <Rule>
           <Name>100-125</Name>
           <Title>100 to 125</Title>
           <ogc:Filter>
           <ogc:And>
             <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>100</ogc:Literal>
             </ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>125</ogc:Literal>
             </ogc:PropertyIsLessThan>
           </ogc:And>
           </ogc:Filter>
       <MaxScaleDenominator>1200000</MaxScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#d9ef8b</CssParameter>
             </Fill>
             <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
             </Stroke>
             </Mark>
             <Size>14</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>
         <Rule>
           <Name>125-150</Name>
           <Title>125 to 150</Title>
           <ogc:Filter>
           <ogc:And>
             <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>125</ogc:Literal>
             </ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>150</ogc:Literal>
             </ogc:PropertyIsLessThan>
           </ogc:And>
           </ogc:Filter>
       <MaxScaleDenominator>1200000</MaxScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#ffffbf</CssParameter>
             </Fill>
            <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
            </Stroke>
             </Mark>
             <Size>14</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>   
         <Rule>
           <Name>150-175</Name>
           <Title>150 to 175</Title>
           <ogc:Filter>
           <ogc:And>
             <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>150</ogc:Literal>
             </ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>175</ogc:Literal>
             </ogc:PropertyIsLessThan>
           </ogc:And>
           </ogc:Filter>
       <MaxScaleDenominator>1200000</MaxScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#fee08b</CssParameter>
             </Fill>
            <Stroke>
              <CssParameter name="stroke">#000000</CssParameter>
              <CssParameter name="stroke-width">1</CssParameter>
            </Stroke>
             </Mark>
             <Size>14</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>   
         <Rule>
           <Name>175-200</Name>
           <Title>175 to 200</Title>
           <ogc:Filter>
           <ogc:And>
             <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>175</ogc:Literal>
             </ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>200</ogc:Literal>
             </ogc:PropertyIsLessThan>
           </ogc:And>
           </ogc:Filter>
       <MaxScaleDenominator>1200000</MaxScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#fdae61</CssParameter>
             </Fill>
            <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
            </Stroke>
             </Mark>
             <Size>14</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>
         <Rule>
           <Name>200-225</Name>
           <Title>200 to 225</Title>
           <ogc:Filter>
           <ogc:And>
             <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>200</ogc:Literal>
             </ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>225</ogc:Literal>
             </ogc:PropertyIsLessThan>
           </ogc:And>
           </ogc:Filter>
       <MaxScaleDenominator>1200000</MaxScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#f46d43</CssParameter>
             </Fill>
            <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
            </Stroke>
             </Mark>
             <Size>14</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>
         <Rule>
           <Name>225-250</Name>
           <Title>225 to 250</Title>
           <ogc:Filter>
           <ogc:And>
             <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>225</ogc:Literal>
             </ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>250</ogc:Literal>
             </ogc:PropertyIsLessThan>
           </ogc:And>
           </ogc:Filter>
       <MaxScaleDenominator>1200000</MaxScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#d73027</CssParameter>
             </Fill>
            <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
            </Stroke>
             </Mark>
             <Size>14</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>
         <Rule>
           <Name>>=250</Name>
           <Title>>=250</Title>
           <ogc:Filter>
           <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>250</ogc:Literal>
           </ogc:PropertyIsGreaterThanOrEqualTo>
           </ogc:Filter>
       <MaxScaleDenominator>1200000</MaxScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#a50026</CssParameter>
             </Fill>
            <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
            </Stroke>
             </Mark>
             <Size>14</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>
        <Rule>
           <Name>NULL</Name>
           <Title>NULL</Title>
           <ogc:Filter>
           <ogc:PropertyIsNull>
             <ogc:PropertyName>error</ogc:PropertyName>
           </ogc:PropertyIsNull>
           </ogc:Filter>
       <MaxScaleDenominator>1200000</MaxScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#000000</CssParameter>
               <CssParameter name="fill-opacity">0</CssParameter>
             </Fill>
              <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
             </Stroke>
             </Mark>
             <Size>14</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>
     
    <!-- Rules for medium scale -->
     
     <Rule>
           <Name>0-25</Name>
       <Title>0 to 25</Title>
           <ogc:Filter>
           <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>25</ogc:Literal>
           </ogc:PropertyIsLessThan>
           </ogc:Filter>
       <MinScaleDenominator>1200000</MinScaleDenominator>
       <MaxScaleDenominator>1950000</MaxScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#0068310</CssParameter>
             </Fill>
              <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
             </Stroke>
             </Mark>
             <Size>12</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>
         <Rule>
           <Name>25-50</Name>
           <Title>25 to 50</Title>
           <ogc:Filter>
           <ogc:And>
             <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>25</ogc:Literal>
             </ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>50</ogc:Literal>
             </ogc:PropertyIsLessThan>
           </ogc:And>
           </ogc:Filter>
       <MinScaleDenominator>1200000</MinScaleDenominator>
       <MaxScaleDenominator>1950000</MaxScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#1a9850</CssParameter>
             </Fill>
              <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
             </Stroke>
             </Mark>
             <Size>12</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>
         <Rule>
           <Name>50-75</Name>
           <Title>50 to 75</Title>
           <ogc:Filter>
           <ogc:And>
             <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>50</ogc:Literal>
             </ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>75</ogc:Literal>
             </ogc:PropertyIsLessThan>
           </ogc:And>
           </ogc:Filter>
       <MinScaleDenominator>1200000</MinScaleDenominator>
       <MaxScaleDenominator>1950000</MaxScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#66bd63</CssParameter>
             </Fill>
             <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
             </Stroke>
             </Mark>
             <Size>12</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>   
         <Rule>
           <Name>75-100</Name>
           <Title>75 to 100</Title>
           <ogc:Filter>
           <ogc:And>
             <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>75</ogc:Literal>
             </ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>100</ogc:Literal>
             </ogc:PropertyIsLessThan>
           </ogc:And>
           </ogc:Filter>
       <MinScaleDenominator>1200000</MinScaleDenominator>
       <MaxScaleDenominator>1950000</MaxScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#a6d96a</CssParameter>
             </Fill>
             <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
             </Stroke>
             </Mark>
             <Size>12</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>   
          <Rule>
           <Name>100-125</Name>
           <Title>100 to 125</Title>
           <ogc:Filter>
           <ogc:And>
             <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>100</ogc:Literal>
             </ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>125</ogc:Literal>
             </ogc:PropertyIsLessThan>
           </ogc:And>
           </ogc:Filter>
       <MinScaleDenominator>1200000</MinScaleDenominator>
       <MaxScaleDenominator>1950000</MaxScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#d9ef8b</CssParameter>
             </Fill>
             <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
             </Stroke>
             </Mark>
             <Size>12</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>
         <Rule>
           <Name>125-150</Name>
           <Title>125 to 150</Title>
           <ogc:Filter>
           <ogc:And>
             <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>125</ogc:Literal>
             </ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>150</ogc:Literal>
             </ogc:PropertyIsLessThan>
           </ogc:And>
           </ogc:Filter>
       <MinScaleDenominator>1200000</MinScaleDenominator>
       <MaxScaleDenominator>1950000</MaxScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#ffffbf</CssParameter>
             </Fill>
            <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
            </Stroke>
             </Mark>
             <Size>12</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>   
         <Rule>
           <Name>150-175</Name>
           <Title>150 to 175</Title>
           <ogc:Filter>
           <ogc:And>
             <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>150</ogc:Literal>
             </ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>175</ogc:Literal>
             </ogc:PropertyIsLessThan>
           </ogc:And>
           </ogc:Filter>
       <MinScaleDenominator>1200000</MinScaleDenominator>
       <MaxScaleDenominator>1950000</MaxScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#fee08b</CssParameter>
             </Fill>
            <Stroke>
              <CssParameter name="stroke">#000000</CssParameter>
              <CssParameter name="stroke-width">1</CssParameter>
            </Stroke>
             </Mark>
             <Size>12</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>   
         <Rule>
           <Name>175-200</Name>
           <Title>175 to 200</Title>
           <ogc:Filter>
           <ogc:And>
             <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>175</ogc:Literal>
             </ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>200</ogc:Literal>
             </ogc:PropertyIsLessThan>
           </ogc:And>
           </ogc:Filter>
       <MinScaleDenominator>1200000</MinScaleDenominator>
       <MaxScaleDenominator>1950000</MaxScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#fdae61</CssParameter>
             </Fill>
            <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
            </Stroke>
             </Mark>
             <Size>12</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>
         <Rule>
           <Name>200-225</Name>
           <Title>200 to 225</Title>
           <ogc:Filter>
           <ogc:And>
             <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>200</ogc:Literal>
             </ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>225</ogc:Literal>
             </ogc:PropertyIsLessThan>
           </ogc:And>
           </ogc:Filter>
       <MinScaleDenominator>1200000</MinScaleDenominator>
       <MaxScaleDenominator>1950000</MaxScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#f46d43</CssParameter>
             </Fill>
            <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
            </Stroke>
             </Mark>
             <Size>12</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>
         <Rule>
           <Name>225-250</Name>
           <Title>225 to 250</Title>
           <ogc:Filter>
           <ogc:And>
             <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>225</ogc:Literal>
             </ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>250</ogc:Literal>
             </ogc:PropertyIsLessThan>
           </ogc:And>
           </ogc:Filter>
       <MinScaleDenominator>1200000</MinScaleDenominator>
       <MaxScaleDenominator>1950000</MaxScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#d73027</CssParameter>
             </Fill>
            <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
            </Stroke>
             </Mark>
             <Size>12</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>
         <Rule>
           <Name>>=250</Name>
           <Title>>=250</Title>
           <ogc:Filter>
           <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>250</ogc:Literal>
           </ogc:PropertyIsGreaterThanOrEqualTo>
           </ogc:Filter>
       <MinScaleDenominator>1200000</MinScaleDenominator>
       <MaxScaleDenominator>1950000</MaxScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#a50026</CssParameter>
             </Fill>
            <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
            </Stroke>
             </Mark>
             <Size>12</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>
        <Rule>
           <Name>NULL</Name>
           <Title>NULL</Title>
           <ogc:Filter>
           <ogc:PropertyIsNull>
             <ogc:PropertyName>error</ogc:PropertyName>
           </ogc:PropertyIsNull>
           </ogc:Filter>
       <MinScaleDenominator>1200000</MinScaleDenominator>
       <MaxScaleDenominator>1950000</MaxScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#000000</CssParameter>
               <CssParameter name="fill-opacity">0</CssParameter>
             </Fill>
              <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
             </Stroke>
             </Mark>
             <Size>12</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>
     
     <!-- Rules for large scale -->
     
     <Rule>
           <Name>0-25</Name>
       <Title>0 to 25</Title>
           <ogc:Filter>
           <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>25</ogc:Literal>
           </ogc:PropertyIsLessThan>
           </ogc:Filter>
       <MinScaleDenominator>1950000</MinScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#0068310</CssParameter>
             </Fill>
              <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
             </Stroke>
             </Mark>
             <Size>6</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>
         <Rule>
           <Name>25-50</Name>
           <Title>25 to 50</Title>
           <ogc:Filter>
           <ogc:And>
             <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>25</ogc:Literal>
             </ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>50</ogc:Literal>
             </ogc:PropertyIsLessThan>
           </ogc:And>
           </ogc:Filter>
       <MinScaleDenominator>1950000</MinScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#1a9850</CssParameter>
             </Fill>
              <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
             </Stroke>
             </Mark>
             <Size>6</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>
         <Rule>
           <Name>50-75</Name>
           <Title>50 to 75</Title>
           <ogc:Filter>
           <ogc:And>
             <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>50</ogc:Literal>
             </ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>75</ogc:Literal>
             </ogc:PropertyIsLessThan>
           </ogc:And>
           </ogc:Filter>
       <MinScaleDenominator>1950000</MinScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#66bd63</CssParameter>
             </Fill>
             <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
             </Stroke>
             </Mark>
             <Size>6</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>   
         <Rule>
           <Name>75-100</Name>
           <Title>75 to 100</Title>
           <ogc:Filter>
           <ogc:And>
             <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>75</ogc:Literal>
             </ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>100</ogc:Literal>
             </ogc:PropertyIsLessThan>
           </ogc:And>
           </ogc:Filter>
       <MinScaleDenominator>1950000</MinScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#a6d96a</CssParameter>
             </Fill>
             <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
             </Stroke>
             </Mark>
             <Size>6</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>   
          <Rule>
           <Name>100-125</Name>
           <Title>100 to 125</Title>
           <ogc:Filter>
           <ogc:And>
             <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>100</ogc:Literal>
             </ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>125</ogc:Literal>
             </ogc:PropertyIsLessThan>
           </ogc:And>
           </ogc:Filter>
       <MinScaleDenominator>1950000</MinScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#d9ef8b</CssParameter>
             </Fill>
             <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
             </Stroke>
             </Mark>
             <Size>6</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>
         <Rule>
           <Name>125-150</Name>
           <Title>125 to 150</Title>
           <ogc:Filter>
           <ogc:And>
             <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>125</ogc:Literal>
             </ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>150</ogc:Literal>
             </ogc:PropertyIsLessThan>
           </ogc:And>
           </ogc:Filter>
       <MinScaleDenominator>1950000</MinScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#ffffbf</CssParameter>
             </Fill>
            <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
            </Stroke>
             </Mark>
             <Size>6</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>   
         <Rule>
           <Name>150-175</Name>
           <Title>150 to 175</Title>
           <ogc:Filter>
           <ogc:And>
             <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>150</ogc:Literal>
             </ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>175</ogc:Literal>
             </ogc:PropertyIsLessThan>
           </ogc:And>
           </ogc:Filter>
       <MinScaleDenominator>1950000</MinScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#fee08b</CssParameter>
             </Fill>
            <Stroke>
              <CssParameter name="stroke">#000000</CssParameter>
              <CssParameter name="stroke-width">1</CssParameter>
            </Stroke>
             </Mark>
             <Size>6</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>   
         <Rule>
           <Name>175-200</Name>
           <Title>175 to 200</Title>
           <ogc:Filter>
           <ogc:And>
             <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>175</ogc:Literal>
             </ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>200</ogc:Literal>
             </ogc:PropertyIsLessThan>
           </ogc:And>
           </ogc:Filter>
       <MinScaleDenominator>1950000</MinScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#fdae61</CssParameter>
             </Fill>
            <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
            </Stroke>
             </Mark>
             <Size>6</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>
         <Rule>
           <Name>200-225</Name>
           <Title>200 to 225</Title>
           <ogc:Filter>
           <ogc:And>
             <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>200</ogc:Literal>
             </ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>225</ogc:Literal>
             </ogc:PropertyIsLessThan>
           </ogc:And>
           </ogc:Filter>
       <MinScaleDenominator>1950000</MinScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#f46d43</CssParameter>
             </Fill>
            <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
            </Stroke>
             </Mark>
             <Size>6</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>
         <Rule>
           <Name>225-250</Name>
           <Title>225 to 250</Title>
           <ogc:Filter>
           <ogc:And>
             <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>225</ogc:Literal>
             </ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyIsLessThan>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>250</ogc:Literal>
             </ogc:PropertyIsLessThan>
           </ogc:And>
           </ogc:Filter>
       <MinScaleDenominator>1950000</MinScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#d73027</CssParameter>
             </Fill>
            <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
            </Stroke>
             </Mark>
             <Size>6</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>
         <Rule>
           <Name>>=250</Name>
           <Title>>=250</Title>
           <ogc:Filter>
           <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>error</ogc:PropertyName>
             <ogc:Literal>250</ogc:Literal>
           </ogc:PropertyIsGreaterThanOrEqualTo>
           </ogc:Filter>
       <MinScaleDenominator>1950000</MinScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#a50026</CssParameter>
             </Fill>
            <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
            </Stroke>
             </Mark>
             <Size>6</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>
        <Rule>
           <Name>NULL</Name>
           <Title>NULL</Title>
           <ogc:Filter>
           <ogc:PropertyIsNull>
             <ogc:PropertyName>error</ogc:PropertyName>
           </ogc:PropertyIsNull>
           </ogc:Filter>
       <MinScaleDenominator>1950000</MinScaleDenominator>
           <PointSymbolizer>
           <Graphic>
             <Mark>
             <WellKnownName>circle</WellKnownName>
             <Fill>
               <CssParameter name="fill">#000000</CssParameter>
               <CssParameter name="fill-opacity">0</CssParameter>
             </Fill>
              <Stroke>
               <CssParameter name="stroke">#000000</CssParameter>
               <CssParameter name="stroke-width">1</CssParameter>
             </Stroke>
             </Mark>
             <Size>6</Size>
           </Graphic>
           </PointSymbolizer>
         </Rule>
         </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
