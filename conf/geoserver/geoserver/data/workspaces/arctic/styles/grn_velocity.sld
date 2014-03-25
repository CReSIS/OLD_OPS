<?xml version="1.0" encoding="ISO-8859-1"?>
<StyledLayerDescriptor version="1.0.0" 
    xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd" 
    xmlns="http://www.opengis.net/sld" 
    xmlns:ogc="http://www.opengis.net/ogc" 
    xmlns:xlink="http://www.w3.org/1999/xlink" 
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <NamedLayer>
    <Name>Two color gradient</Name>
    <UserStyle>
      <Title>SLD Cook Book: Two color gradient</Title>
      <FeatureTypeStyle>
        <Rule>
          <RasterSymbolizer>
            <ColorMap>
              <ColorMapEntry color="#000000" quantity="-0.1" opacity="0"/>
              <ColorMapEntry color="#815E54" quantity="0" label="0 m/yr"/>
              <ColorMapEntry color="#447F56" quantity="1" label="10 m/yr"/>
              <ColorMapEntry color="#175B83" quantity="2" label="100 m/yr"/>
              <ColorMapEntry color="#250080" quantity="2.3" label="200 m/yr"/>
              <ColorMapEntry color="#840074" quantity="3" label="1000 m/yr"/>
              <ColorMapEntry color="#810003" quantity="4.2" label="13000 m/yr"/>
            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>