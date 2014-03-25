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
              <ColorMapEntry color="#FFFFFF" quantity="0"/>
              <ColorMapEntry color="#4D4D4D" quantity="1"/>
              <ColorMapEntry color="#B8B8B8" quantity="70"/>
              <ColorMapEntry color="#E3E3E3" quantity="140"/>
              <ColorMapEntry color="#FF5C5C" quantity="210"/>
              <ColorMapEntry color="#FF3333" quantity="240"/>
              <ColorMapEntry color="#FF0000" quantity="280"/>
            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>