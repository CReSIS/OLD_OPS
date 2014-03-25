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
              <ColorMapEntry color="#000000" quantity="-9999" opacity="0"/>
              <ColorMapEntry color="#005582" quantity="-1100"/>
              <ColorMapEntry color="#0599C6" quantity="-850"/>
              <ColorMapEntry color="#61CBB5" quantity="-600"/>
              <ColorMapEntry color="#B4F5B1" quantity="-350"/>
              <ColorMapEntry color="#A7D0A1" quantity="-100"/>
              <ColorMapEntry color="#597032" quantity="150"/>
              <ColorMapEntry color="#847037" quantity="400"/>
              <ColorMapEntry color="#AE9A47" quantity="650"/>
              <ColorMapEntry color="#E6D25C" quantity="900"/>
              <ColorMapEntry color="#FAE977" quantity="1150"/>
              <ColorMapEntry color="#FBED92" quantity="1400"/>
              <ColorMapEntry color="#FCF2AE" quantity="1650"/>
              <ColorMapEntry color="#FDF8B5" quantity="1900"/>
            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>