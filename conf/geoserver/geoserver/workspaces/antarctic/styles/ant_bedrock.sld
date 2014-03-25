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
              <ColorMapEntry color="#000652" quantity="-2800"/>
              <ColorMapEntry color="#001C88" quantity="-2400"/>
              <ColorMapEntry color="#002B9E" quantity="-2000"/>
              <ColorMapEntry color="#0075DB" quantity="-1500"/>
              <ColorMapEntry color="#00A7ED" quantity="-1000"/>
              <ColorMapEntry color="#00FFF3" quantity="-500"/>
              <ColorMapEntry color="#94FDA6" quantity="0"/>
              <ColorMapEntry color="#FAF81B" quantity="500"/>
              <ColorMapEntry color="#FFB800" quantity="1000"/>
              <ColorMapEntry color="#FF3500" quantity="1500"/>
              <ColorMapEntry color="#D20000" quantity="2000"/>
              <ColorMapEntry color="#840200" quantity="2400"/>
              <ColorMapEntry color="#EEAF1F" quantity="2800"/>
              <ColorMapEntry color="#000000" quantity="32767" opacity="0"/>
            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>