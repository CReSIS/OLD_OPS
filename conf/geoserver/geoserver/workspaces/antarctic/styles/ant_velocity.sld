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
              <ColorMapEntry color="#000000" quantity="-2" opacity="0"/>
              <ColorMapEntry color="#6a1621" quantity="-1.999"/>
              <ColorMapEntry color="#5a4636" quantity="0.69"/>
              <ColorMapEntry color="#65462b" quantity="0.7"/>
              <ColorMapEntry color="#65462b" quantity="0.9"/>
              <ColorMapEntry color="#4c6b15" quantity="1.1"/>
              <ColorMapEntry color="#008033" quantity="1.2"/>
              <ColorMapEntry color="#008033" quantity="1.4"/>
              <ColorMapEntry color="#00805A" quantity="1.6"/>
              <ColorMapEntry color="#008080" quantity="1.8"/>
              <ColorMapEntry color="#005980" quantity="2.0"/>
              <ColorMapEntry color="#003380" quantity="2.1"/>
              <ColorMapEntry color="#000D80" quantity="2.2"/>
              <ColorMapEntry color="#1A0080" quantity="2.3"/>
              <ColorMapEntry color="#400080" quantity="2.4"/>
              <ColorMapEntry color="#660080" quantity="2.5"/>
              <ColorMapEntry color="#800073" quantity="2.6"/>
              <ColorMapEntry color="#80004D" quantity="2.8"/>
              <ColorMapEntry color="#800027" quantity="3"/>
            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>